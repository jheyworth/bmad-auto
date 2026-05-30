"""End-to-end driver for /bmad-auto.

Drives an interactive `claude` session inside a tmux pane, pointed at a
fixture working directory, and waits for the orchestrator to reach a
terminal state. Used by the four e2e test variants (T1-T4).

Design constraints (from project CLAUDE.md):
- Must NOT use `claude -p` / headless print mode anywhere in the
  driving harness. The orchestrator runs in an interactive Claude
  session inside tmux.
- Sub-skill resolution requires `.claude/skills/` reachable from cwd.
  The driver symlinks the automator repo's `.claude/` and `_bmad/`
  into the fixture tmpdir so the orchestrator can resolve sub-skills
  and TEA config from within the isolated working directory.

Public API:
    prepare_fixture_repo(...)  Materialize a fixture variant into a tmpdir.
    spawn_orchestrator(...)    Start the tmux+claude session, paste invocation.
    wait_for_terminal_state(...)  Poll sidecars until completion / HALT / timeout.
    teardown(...)              Kill the tmux session.

The driver is stdlib-only, Python 3.11+, no external test dependencies
beyond pytest (which itself is opt-in via `-m e2e`).
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

# --- Constants ---------------------------------------------------------------

_DRIVER_PATH = pathlib.Path(__file__).resolve()
# Walk up: tests/ -> scripts/ -> bmad-auto/ -> skills/ -> automator-repo/
AUTOMATOR_REPO = _DRIVER_PATH.parents[4]

# Files / dirs the driver symlinks from the automator repo into the fixture
# tmpdir so the orchestrator's preflight + sub-skill resolution succeeds.
SYMLINK_TARGETS = (".claude", "_bmad")

# Wall-clock budgets (seconds) per terminal-state variant.
DEFAULT_TIMEOUT_SECONDS = {
    "preflight-halt": 180,       # T3: orchestrator boots, reads SKILL.md, runs preflight bash probes
    "phase1-halt": 900,          # T2: Phase 1.e parallel scan + headless FAIL HALT
    "happy-headless": 5400,      # T1: full epic, 90 min budget
    "happy-express": 5400,       # T4: same as headless but with Express consent
}

# Poll cadence for sidecar checks (seconds).
SIDECAR_POLL_INTERVAL = 10

# Wait for claude prompt to render before sending the /bmad-auto invocation.
CLAUDE_PROMPT_WARMUP_SECONDS = 8


# --- Result dataclasses ------------------------------------------------------


TerminalState = Literal[
    "digest-rendered",      # Phase 4.e ran (happy path, T1/T4)
    "phase1-halted",        # Stage 1.e HALT (T2)
    "preflight-halted",     # Stage 0 HALT (T3)
    "timeout",              # Wall-clock budget exhausted with no terminal state
    "tmux-died",            # tmux session disappeared unexpectedly
]


@dataclass
class DriverResult:
    """Outcome of an e2e run. Consumed by the assertion library."""

    terminal_state: TerminalState
    fixture_root: pathlib.Path
    session_name: str
    run_id: str | None
    elapsed_seconds: float
    pane_capture: str = ""
    sprint_status_snapshots: list[tuple[float, dict[str, str]]] = field(default_factory=list)


# --- Fixture preparation -----------------------------------------------------


def prepare_fixture_repo(
    fixture_source: pathlib.Path,
    tmpdir: pathlib.Path,
    *,
    overlay_files: dict[str, str] | None = None,
    omit_files: tuple[str, ...] = (),
) -> pathlib.Path:
    """Materialize a fixture variant into tmpdir.

    1. Copy fixture_source/* into tmpdir (omitting `omit_files`)
    2. Apply `overlay_files` (relative-path -> content) — used by variants
       that are small diffs on top of `happy/`
    3. git init + initial commit so the orchestrator's Stage 3 setup #1
       can record HEAD as `epic-K-start.sha`
    4. Symlink .claude/ and _bmad/ from the automator repo

    Returns the absolute path to the prepared fixture root.
    """

    fixture_source = fixture_source.resolve()
    tmpdir = tmpdir.resolve()
    tmpdir.mkdir(parents=True, exist_ok=True)

    # 1 + 2: copy tree, then apply overrides/omissions
    omit_set = {os.path.normpath(p) for p in omit_files}
    for src_path in fixture_source.rglob("*"):
        if not src_path.is_file():
            continue
        rel = src_path.relative_to(fixture_source)
        if os.path.normpath(str(rel)) in omit_set:
            continue
        dst = tmpdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dst)

    if overlay_files:
        for rel_path, content in overlay_files.items():
            dst = tmpdir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content)

    # 3: git init + commit (sub-shell to keep cwd untouched)
    subprocess.run(["git", "init", "--quiet"], cwd=tmpdir, check=True)
    subprocess.run(
        ["git", "-c", "user.email=e2e@bmad-auto", "-c", "user.name=bmad-auto-e2e",
         "add", "-A"],
        cwd=tmpdir, check=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=e2e@bmad-auto", "-c", "user.name=bmad-auto-e2e",
         "commit", "--quiet", "--allow-empty", "-m", "e2e fixture initial"],
        cwd=tmpdir, check=True,
    )

    # 4: symlinks for skill + config resolution
    for target in SYMLINK_TARGETS:
        src = AUTOMATOR_REPO / target
        if not src.exists():
            raise RuntimeError(
                f"Required symlink source missing: {src}. Run the driver from "
                f"the automator repo with .claude/ and _bmad/ populated."
            )
        link = tmpdir / target
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(src)

    return tmpdir


# --- tmux + claude session ---------------------------------------------------


def _run_tmux(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """Thin wrapper around `tmux <args>`. Surfaces stderr on failure."""
    result = subprocess.run(
        ["tmux", *args], capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"tmux {' '.join(args)} failed ({result.returncode}): "
            f"stderr={result.stderr.strip()}"
        )
    return result


def _session_exists(session: str) -> bool:
    result = _run_tmux(["has-session", "-t", session], check=False)
    return result.returncode == 0


def spawn_orchestrator(
    fixture_root: pathlib.Path,
    *,
    invocation: str,
    session_name: str | None = None,
) -> str:
    """Spawn a tmux session with `claude --dangerously-skip-permissions`
    rooted at fixture_root, then paste `invocation` (e.g.
    `/bmad-auto --headless --epics 99`) once the prompt is ready.

    Returns the session name. The session continues running after this
    function returns — the caller is expected to call
    `wait_for_terminal_state(...)` to drive it forward, then `teardown`.
    """

    if session_name is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        session_name = f"bmad-auto-e2e-{stamp}-{os.getpid()}"

    if _session_exists(session_name):
        raise RuntimeError(f"tmux session name collision: {session_name}")

    # tmux passes a single string to the default shell, so the command
    # needs to be the full invocation in one arg. Using -c sets cwd.
    _run_tmux([
        "new-session", "-d",
        "-s", session_name,
        "-x", "220", "-y", "60",
        "-c", str(fixture_root),
        "claude --dangerously-skip-permissions",
    ])

    # Wait for claude to render its workspace-trust prompt + first paint.
    time.sleep(CLAUDE_PROMPT_WARMUP_SECONDS)

    # Dismiss the workspace-trust prompt. Fresh directories trigger
    # "Is this a project you created or one you trust?" with "Yes, I
    # trust this folder" pre-selected — Enter accepts it. If the dir is
    # already trusted (test re-run), Enter at the idle prompt is a no-op.
    _run_tmux(["send-keys", "-t", session_name, "Enter"])
    time.sleep(3)

    # Paste the invocation via load-buffer / paste-buffer for reliability.
    buf_file = fixture_root / ".bmad-auto-e2e-invocation.txt"
    buf_file.write_text(invocation)
    _run_tmux(["load-buffer", "-t", session_name, str(buf_file)])
    _run_tmux(["paste-buffer", "-t", session_name])
    # Brief settle, then submit.
    time.sleep(1.5)
    _run_tmux(["send-keys", "-t", session_name, "Enter"])
    buf_file.unlink(missing_ok=True)

    return session_name


def send_input(session: str, text: str, *, submit: bool = True) -> None:
    """Send `text` to the claude session via paste-buffer + send-keys.

    Used by T4 to respond to the Express consent `[y/N]` prompt. paste-buffer
    is more reliable than send-keys for arbitrary text (avoids meta-key
    escaping issues).
    """
    if not text:
        if submit:
            _run_tmux(["send-keys", "-t", session, "Enter"])
        return

    # tmux load-buffer requires a file or stdin
    proc = subprocess.run(
        ["tmux", "load-buffer", "-t", session, "-"],
        input=text, text=True, check=True,
    )
    _run_tmux(["paste-buffer", "-t", session])
    if submit:
        time.sleep(0.5)
        _run_tmux(["send-keys", "-t", session, "Enter"])


def wait_for_pane_marker(
    session: str,
    *,
    marker: str,
    timeout_seconds: int = 120,
    poll_interval: float = 2.0,
) -> bool:
    """Block until `marker` appears in the captured pane, or timeout.

    Returns True on detection, False on timeout. Used by T4 to wait for
    the `Proceed?` prompt before sending `y`.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not _session_exists(session):
            return False
        if marker in capture_pane(session):
            return True
        time.sleep(poll_interval)
    return False


def capture_pane(session: str, *, history_lines: int = 2000) -> str:
    """Capture the full visible + scrollback pane content as text."""
    result = _run_tmux([
        "capture-pane", "-t", session, "-p",
        "-S", f"-{history_lines}",
    ], check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def teardown(session: str) -> None:
    """Idempotently kill the tmux session."""
    if _session_exists(session):
        _run_tmux(["kill-session", "-t", session], check=False)


# --- Terminal-state detection ------------------------------------------------


def _read_sprint_status(fixture_root: pathlib.Path) -> dict[str, str]:
    """Minimal YAML-ish reader for sprint-status.yaml.

    Matches the format `bmad-auto-helper.py read_sprint_status` produces:
        development_status:
          KEY: VALUE
    """
    path = fixture_root / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml"
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    in_block = False
    for line in path.read_text().splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue
        if stripped.startswith("development_status:"):
            in_block = True
            continue
        if in_block:
            if not line.startswith(" "):
                in_block = False
                continue
            if ":" in stripped:
                k, _, v = stripped.strip().partition(":")
                out[k.strip()] = v.strip()
    return out


def _find_run_digest(fixture_root: pathlib.Path) -> pathlib.Path | None:
    """Return the path to run-digest-<runId>.md if Stage 4.e completed."""
    run_state = fixture_root / "_bmad-output" / ".run-state"
    if not run_state.is_dir():
        return None
    candidates = sorted(run_state.glob("run-digest-*.md"))
    return candidates[-1] if candidates else None


def _is_preflight_halt(pane: str) -> bool:
    """Detect Stage 0 HALT from pane output.

    Markers are case-insensitive substring checks. Claude strips backticks
    when rendering markdown to the TUI, so we match the bare phrase.
    """
    lowered = pane.lower()
    markers = (
        "epics.md not found",
        "epics.md is missing",
        "missing epics.md",
        "cannot find epics.md",
        "bmad-create-epics-and-stories",  # the remediation hint
        "tmux not found",
        "python3 >= 3.11 not found",
        "tea module not installed",
        # In headless mode, missing interactive-only skills HALT with this:
        "halt",
    )
    return any(m.lower() in lowered for m in markers)


def _is_phase1_halt(pane: str) -> bool:
    """Detect Stage 1.e FAIL HALT from pane output."""
    # The headless-mode FAIL HALT directive emits a recognizable phrase.
    markers = (
        "Headless cannot silently launch Phase 2 over a FAIL",
        "FAIL finding HALTs Headless",
        "Phase 1 hardening findings",  # weaker signal — present in both pass and fail
    )
    # Require the stronger markers to avoid false positives on the table header.
    return any(m in pane for m in markers[:2])


def wait_for_terminal_state(
    session: str,
    fixture_root: pathlib.Path,
    *,
    expected: TerminalState,
    timeout_seconds: int,
) -> DriverResult:
    """Poll fixture sidecars + pane content until a terminal state or timeout.

    Terminal states recognized:
    - `digest-rendered`: `.run-state/run-digest-*.md` exists
    - `phase1-halted`: pane contains the Stage 1.e FAIL HALT marker AND no digest
    - `preflight-halted`: pane contains a Stage 0 HALT marker AND no digest
    - `timeout`: budget exhausted
    - `tmux-died`: session no longer exists

    Returns a DriverResult capturing the final state plus diagnostic info.
    """

    started = time.time()
    snapshots: list[tuple[float, dict[str, str]]] = []
    run_id: str | None = None

    while True:
        elapsed = time.time() - started
        if elapsed > timeout_seconds:
            pane = capture_pane(session)
            return DriverResult(
                terminal_state="timeout",
                fixture_root=fixture_root,
                session_name=session,
                run_id=run_id,
                elapsed_seconds=elapsed,
                pane_capture=pane,
                sprint_status_snapshots=snapshots,
            )

        if not _session_exists(session):
            return DriverResult(
                terminal_state="tmux-died",
                fixture_root=fixture_root,
                session_name=session,
                run_id=run_id,
                elapsed_seconds=elapsed,
                pane_capture="",
                sprint_status_snapshots=snapshots,
            )

        # Snapshot sprint-status for monotonicity assertions.
        snapshots.append((elapsed, _read_sprint_status(fixture_root)))

        # Check the digest sidecar — the strongest happy-path completion signal.
        digest = _find_run_digest(fixture_root)
        if digest is not None:
            if run_id is None:
                run_id = digest.stem.removeprefix("run-digest-")
            pane = capture_pane(session)
            return DriverResult(
                terminal_state="digest-rendered",
                fixture_root=fixture_root,
                session_name=session,
                run_id=run_id,
                elapsed_seconds=elapsed,
                pane_capture=pane,
                sprint_status_snapshots=snapshots,
            )

        # Check pane for HALT markers (only relevant for HALT-expecting tests).
        pane = capture_pane(session)
        if expected == "preflight-halted" and _is_preflight_halt(pane):
            return DriverResult(
                terminal_state="preflight-halted",
                fixture_root=fixture_root,
                session_name=session,
                run_id=run_id,
                elapsed_seconds=elapsed,
                pane_capture=pane,
                sprint_status_snapshots=snapshots,
            )
        if expected == "phase1-halted" and _is_phase1_halt(pane):
            return DriverResult(
                terminal_state="phase1-halted",
                fixture_root=fixture_root,
                session_name=session,
                run_id=run_id,
                elapsed_seconds=elapsed,
                pane_capture=pane,
                sprint_status_snapshots=snapshots,
            )

        time.sleep(SIDECAR_POLL_INTERVAL)


# --- High-level convenience --------------------------------------------------


def run_e2e(
    fixture_source: pathlib.Path,
    tmpdir: pathlib.Path,
    *,
    invocation: str,
    expected: TerminalState,
    timeout_key: str,
    overlay_files: dict[str, str] | None = None,
    omit_files: tuple[str, ...] = (),
) -> DriverResult:
    """One-shot helper: prepare fixture, spawn, wait, teardown.

    The four test variants compose this with their variant-specific
    invocation + overlay + expected-terminal-state.
    """

    fixture_root = prepare_fixture_repo(
        fixture_source, tmpdir,
        overlay_files=overlay_files,
        omit_files=omit_files,
    )

    session = spawn_orchestrator(fixture_root, invocation=invocation)
    try:
        result = wait_for_terminal_state(
            session, fixture_root,
            expected=expected,
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS[timeout_key],
        )
    finally:
        teardown(session)

    return result
