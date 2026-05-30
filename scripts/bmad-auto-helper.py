#!/usr/bin/env python3
"""LLM-orchestrator helper for /bmad-auto.

Owns the systems-layer concerns that previously lived as ~150 lines of
SKILL.md Stage 3.4 prose: spawning the tmux-hosted Claude session,
monitoring it (sprint-status flip + sidecar + capture-pane grep with
three structural guards + stall fingerprinting), surfacing a single
JSON terminal-state result, deriving adaptive cadence, and killing
sessions.

Stdlib-only, Python 3.11+, single file. The orchestrator (SKILL.md)
shells out to this helper and consumes JSON; the helper stays out of
the LLM's polling loop.

Subcommands:
    spawn           Start a tmux-hosted Claude session for a story.
    monitor         Poll until terminal state (completed/halted/stalled/timeout).
    halt-check      One-shot HALT check (sidecar-primary + grep-fallback).
    derive-cadence  Map story-count to poll cadence in seconds.
    kill            Idempotently kill a tmux session.

Exit codes:
    0  success
    1  generic error
    2  timeout
    3  not-found

JSON output goes to stdout (per subcommand contract); logs go to
stderr (gated by --verbose).
"""

# Pattern reference: bmad-automator/skills/bmad-story-automator/src/story_automator/core/tmux_runtime.py (MIT)

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timezone

# --- Exit codes --------------------------------------------------------------

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_TIMEOUT = 2
EXIT_NOT_FOUND = 3

# --- Cadence derivation constants --------------------------------------------
#
# Tiered story-count → poll-cadence (seconds) lookup. Matches SKILL.md Stage 3
# setup #4 prose: more stories ⇒ tighter cadence to amortize total wait.
# Each tier is (max_story_count_inclusive, cadence_seconds); the first tier
# whose upper bound is ≥ story_count wins. Counts above the last tier fall
# through to CADENCE_HIGH_VOLUME.
CADENCE_TIERS: tuple[tuple[int, int], ...] = (
    (3, 45),   # 1..3 stories → 45s
    (7, 30),   # 4..7 stories → 30s
)
CADENCE_HIGH_VOLUME = 20  # 8+ stories

# --- HALT detection constants ------------------------------------------------
#
# Seven trigger classes, in evaluation order. Each entry is
# (class_name, [substring_alias, ...]). All matches are case-insensitive.
# Aliases are substrings searched against the candidate line.
#
# `HALT` is a special case: the bare token does not pattern-match like the
# others. It is handled in Guard C (`_halt_literal_ok`) and only fires when
# the line is a clear status emission, not when `HALT` appears as an English
# noun inside instructional prose. The class name is `halt_literal`.
HALT_TRIGGERS: list[tuple[str, list[str]]] = [
    ("intent_gap", ["intent_gap", "intent gap"]),
    ("bad_spec", ["bad_spec", "bad spec", "spec is bad"]),
    ("vcs_dirty", ["vcs dirty", "vcs is dirty", "dirty working tree"]),
    ("wrong_branch", ["wrong branch", "on the wrong branch"]),
    (
        "loopback_overflow",
        [
            ">5 loopbacks",
            "more than 5 loopbacks",
            "loopback overflow",
            "loopback count exceeded",
            "loopback ceiling",
        ],
    ),
    ("halt_literal", ["halt"]),
    (
        "red_tests_failing",
        [
            "red tests still failing",
            "tests still red",
            "red tests failing",
            "tests not green",
        ],
    ),
]

# Conditional / modal prefixes that mark a line as instructional prose
# ("if tests are still red, HALT"). Lowercase; matched after stripping
# leading whitespace and optional bullet markers.
PROSE_MODALS: tuple[str, ...] = ("if ", "when ", "should ", "must ", "unless ")

# Status-emission lines (`Status: HALTED.` / `Reason: intent_gap`) are the
# authoritative form. Prose-suppression must NOT fire on them.
STATUS_EMISSION_RE = re.compile(r"^\s*(Status|Reason)\s*:", re.IGNORECASE)

# Bare `HALT` at line start. Used by Guard C — the token only counts as a
# HALT when it heads a short status-shaped line, not when it sits inside
# longer English prose.
HALT_LITERAL_RE = re.compile(r"^\s*HALT\b", re.IGNORECASE)

# Default tail window — last N lines of the captured pane. Matches SKILL.md
# Stage 3.4 prose ("the recent-output window").
DEFAULT_TAIL_LINES = 60

# Sidecar required-field set per autonomous-mode-directive #8.
SIDECAR_REQUIRED_FIELDS: tuple[str, ...] = (
    "status",
    "reason",
    "iteration",
    "files_affected",
    "timestamp",
    "storyId",
)

# --- Spawn warmup constants --------------------------------------------------
#
# Claude Code v2 (verified against 2.1.153) needs ~10s after `tmux new-session
# … claude --dangerously-skip-permissions` to (a) render its welcome banner
# and (b) display the workspace-trust prompt for a previously-untrusted dir.
# Pasting before this is complete causes the paste content to be partially
# eaten by the trust-prompt menu and/or the welcome screen, leaving the
# subsequent `C-m` non-submitting because the input box never settled into a
# clean ready state. Empirically reproduced in the bmad-auto e2e harness;
# fix mirrors the e2e driver's `CLAUDE_PROMPT_WARMUP_SECONDS`.
DEFAULT_CLAUDE_BOOT_WAIT_SECONDS = 10.0
DEFAULT_TRUST_PROMPT_SETTLE_SECONDS = 3.0

# Time between `tmux paste-buffer` and `tmux send-keys C-m` (submit). When
# Claude Code v2 folds a long paste into `[Pasted text #N +M lines]`
# placeholders for display, the next `C-m` is silently swallowed unless the
# TUI has had a moment to settle the placeholder render. 2s is enough
# empirically (5KB autonomous-mode-directives.md folds into 8 placeholders
# and submits cleanly with this delay; without it, the input box accumulates
# the paste content but never submits).
DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS = 2.0

# --- Logging -----------------------------------------------------------------

_VERBOSE = False


def log(message: str) -> None:
    """Emit a verbose log line to stderr when --verbose is set."""
    if _VERBOSE:
        print(message, file=sys.stderr)


# --- Common helpers ----------------------------------------------------------


def run_tmux(args: list[str]) -> subprocess.CompletedProcess:
    """Run a tmux command and return the CompletedProcess.

    Captures stdout/stderr as text; does not raise on non-zero exit.
    Callers are responsible for interpreting returncode + streams.
    """
    return subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
    )


def read_sidecar(path: pathlib.Path) -> dict | None:
    """Read and parse a JSON sidecar file.

    Returns the parsed dict on success, or None if the path does not
    exist or cannot be parsed as JSON. Other I/O errors are also
    treated as None — callers fall back to capture-pane grep.
    """
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


# Candidate paths for sprint-status.yaml, in priority order. The
# canonical location (per SKILL.md Stage 0 probe + the
# bmad-sprint-planning producer) is
# `_bmad-output/implementation-artifacts/sprint-status.yaml`. The
# `.run-state/` location is kept as a fallback so an alternate convention
# (mentioned in the T1.4 task description) does not silently fail.
SPRINT_STATUS_CANDIDATES: tuple[str, ...] = (
    "_bmad-output/implementation-artifacts/sprint-status.yaml",
    "_bmad-output/.run-state/sprint-status.yaml",
)


def _sprint_status_path(repo_root: pathlib.Path) -> pathlib.Path | None:
    """Return the first existing sprint-status.yaml candidate, or None."""
    for relative in SPRINT_STATUS_CANDIDATES:
        candidate = repo_root / relative
        if candidate.exists():
            return candidate
    return None


# `<key>:` or `<key>: <value>`. Captures the indent, key, and value
# (value may be empty when the line is a block opener like `3-1-tracer:`).
# story-id may contain letters, digits, dots, hyphens, underscores.
_FLAT_STORY_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<key>[A-Za-z0-9][A-Za-z0-9._\-]*)\s*:\s*(?P<value>.*?)\s*$"
)
# `status: <value>` line (nested form). Captured indent comes from the
# outer match — we just need the status value here.
_STATUS_LINE_RE = re.compile(r"^[ \t]+status\s*:\s*(?P<value>\S.*?)\s*$", re.IGNORECASE)


def read_sprint_status(repo_root: pathlib.Path) -> dict:
    """Read sprint-status.yaml and return {story_id: status_lowercase}.

    Intentionally minimal hand-rolled parser — stdlib has no YAML reader
    and we own the producer (bmad-sprint-planning). Handles two shapes
    that appear in fixtures and prod artifacts:

      Flat form:
          development_status:
            99-1-foo: done
            99-2-bar: in-progress

      Nested form:
          development_status:
            3-1-tracer:
              title: "Tracer: end-to-end rate-limit path"
              status: done

    Strategy: walk lines under any `development_status:` block (the
    canonical container) AND tolerate flat top-level keys (legacy form).
    For each candidate key line, capture either the inline value or
    scan subsequent more-indented lines for a `status:` line, stopping
    at the next key at the same-or-lower indent.

    Returns {} on:
      - missing file (callers keep polling)
      - any parse-time exception (logged warning; callers keep polling)
    """
    path = _sprint_status_path(repo_root)
    if path is None:
        return {}

    try:
        text = path.read_text()
    except OSError as exc:
        log(f"read_sprint_status: read failed: {exc}")
        return {}

    try:
        return _parse_sprint_status(text)
    except Exception as exc:  # pragma: no cover - defensive
        log(f"read_sprint_status: parse failed: {exc}")
        return {}


def _parse_sprint_status(text: str) -> dict:
    """Minimal YAML-ish parser. See read_sprint_status() docstring.

    The parser collects story status entries from inside the
    `development_status:` block. If `development_status:` is absent
    (legacy/loose form), it falls back to collecting flat top-level
    `<key>: <value>` pairs at indent 0.
    """
    result: dict[str, str] = {}
    lines = text.splitlines()
    n = len(lines)

    # Find the `development_status:` block if present.
    dev_start = -1
    dev_indent = -1
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("#") or not stripped:
            continue
        m = re.match(r"^([ \t]*)development_status\s*:\s*(.*)$", raw)
        if m and (m.group(2).strip() == "" or m.group(2).strip().startswith("#")):
            dev_start = idx + 1
            dev_indent = len(m.group(1))
            break

    if dev_start >= 0:
        # Scan inside development_status until indent returns to ≤ dev_indent.
        _collect_block(lines, dev_start, dev_indent, n, result)
        return result

    # Legacy flat form — no development_status: container. Treat all
    # indent-0 `<key>: <scalar>` pairs as story status entries.
    _collect_flat_top_level(lines, n, result)
    return result


def _collect_block(
    lines: list[str], start: int, parent_indent: int, n: int, result: dict[str, str]
) -> None:
    """Collect story-status entries from a YAML block whose parent
    key sits at `parent_indent`. We accept story rows at any indent
    greater than parent_indent (so both flat `key: status` and
    nested `key:\n  status: <value>` forms are picked up).
    """
    i = start
    # The first non-blank, non-comment child sets the expected child indent.
    child_indent: int | None = None
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        cur_indent = len(raw) - len(raw.lstrip(" \t"))
        if cur_indent <= parent_indent:
            return  # exited the block
        if child_indent is None:
            child_indent = cur_indent
        # Only consider rows at exactly child_indent as story keys.
        if cur_indent != child_indent:
            i += 1
            continue
        m = _FLAT_STORY_RE.match(raw)
        if not m:
            i += 1
            continue
        key = m.group("key")
        value = m.group("value")

        if value == "" or value is None:
            # Block opener (nested form). Look ahead for a `status:` line
            # at deeper indent before we hit a sibling at child_indent.
            j = i + 1
            child_status: str | None = None
            while j < n:
                nxt = lines[j]
                nxt_stripped = nxt.strip()
                if not nxt_stripped or nxt_stripped.startswith("#"):
                    j += 1
                    continue
                nxt_indent = len(nxt) - len(nxt.lstrip(" \t"))
                if nxt_indent <= cur_indent:
                    break
                sm = _STATUS_LINE_RE.match(nxt)
                if sm:
                    child_status = sm.group("value").strip().strip('"').strip("'")
                    break
                j += 1
            if child_status is not None:
                result[key] = child_status.lower()
            i += 1
            continue

        # Inline form: `<key>: <value>`. Strip quotes; ignore obvious
        # metadata (values with whitespace or `/`).
        value_clean = value.strip().strip('"').strip("'")
        if " " in value_clean or "/" in value_clean:
            i += 1
            continue
        result[key] = value_clean.lower()
        i += 1


def _collect_flat_top_level(lines: list[str], n: int, result: dict[str, str]) -> None:
    """Legacy fallback: collect indent-0 `<key>: <scalar>` pairs."""
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            continue
        m = _FLAT_STORY_RE.match(raw)
        if not m:
            continue
        value = m.group("value")
        if value == "" or value is None:
            continue
        value_clean = value.strip().strip('"').strip("'")
        if " " in value_clean or "/" in value_clean:
            continue
        result[m.group("key")] = value_clean.lower()


def _story_status(sprint_status: dict, story_id: str) -> str | None:
    """Look up a story's status in the sprint-status map.

    Three-tier resolution:
      1. Exact key match (fast path; preserves existing behavior).
      2. Case-insensitive exact match (preserves existing behavior).
      3. Segment-boundary prefix match — handles the convention mismatch
         between the orchestrator (short storyId like ``100-2``, matching
         session names + sidecar filenames) and the sprint-status
         producer (``bmad-sprint-planning`` writes full slugs like
         ``100-2-validation-sandbox-paths-cmd``). The match requires a
         literal ``-`` after ``story_id`` so the epic-id form (``100``)
         cannot incorrectly match story keys (``100-2-foo``). When two
         keys would prefix-match (theoretical collision case), returns
         ``None`` rather than guessing — fail-safe behavior keeps the
         monitor polling rather than racing to a wrong story's status.

    Provenance: bmad-auto-v5-smoke-fix-3.md T4
    (smoke-run-3 Bug 2 — monitor missed sprint-status flip because the
    matcher couldn't bridge the two conventions).
    """
    if not story_id:
        return None
    if story_id in sprint_status:
        return sprint_status[story_id]
    target = story_id.lower()
    for key, value in sprint_status.items():
        if key.lower() == target:
            return value
    prefix = target + "-"
    matches = [
        key for key in sprint_status if key.lower().startswith(prefix)
    ]
    if len(matches) == 1:
        return sprint_status[matches[0]]
    return None


def _find_repo_root() -> pathlib.Path:
    """Walk up from CWD looking for `_bmad-output`. Fall back to CWD."""
    cwd = pathlib.Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "_bmad-output").is_dir():
            return candidate
    return cwd


# --- HALT-detection guards (Stage 3.4 structural guards) ---------------------


def _apply_tail_window(text: str, n: int) -> list[str]:
    """Guard A — keep only the last `n` lines of the captured pane.

    /goal directive prose lives at the top of the buffer when the session
    is freshly spawned and scrolls past this window once meaningful work
    begins. Matches outside the tail are prompt scrollback, not events.
    """
    if n <= 0:
        return []
    lines = text.splitlines()
    if len(lines) <= n:
        return lines
    return lines[-n:]


def _is_prose_suppressed(line: str, trigger: str) -> bool:
    """Guard B — suppress instructional / prose lines from firing.

    Suppresses when:
      - Line is a markdown-quote (leading `>` + space).
      - Line begins with a conditional/modal keyword after optional
        whitespace + optional bullet marker (`-`, `*`).
      - The trigger token appears wrapped in backticks or quotation marks
        on this line (documentation prose referring to the token rather
        than the token being emitted).

    Exception: if the line clearly looks like a status emission
    (`Status: ...` / `Reason: ...`), prose-suppression does NOT fire.
    Status emissions are authoritative.
    """
    if STATUS_EMISSION_RE.match(line):
        return False

    stripped = line.lstrip()

    # Markdown quote prefix (claude echo of /goal directive).
    if stripped.startswith(">"):
        return True

    # Strip an optional bullet marker so "- if ..." / "* when ..." catch.
    leading = stripped
    if leading[:1] in ("-", "*"):
        leading = leading[1:].lstrip()
    lower = leading.lower()
    if any(lower.startswith(modal) for modal in PROSE_MODALS):
        return True

    # Trigger token in backticks or straight quotes on this line.
    quoted_forms = (f"`{trigger}`", f'"{trigger}"', f"'{trigger}'")
    line_lower = line.lower()
    trig_lower = trigger.lower()
    if any(q.lower() in line_lower for q in quoted_forms):
        return True

    # Also catch the case where the alias appears as a quoted phrase even
    # though the canonical form differs (e.g. `"halt"` for the halt class).
    # Already covered by the loop above since `trigger` is the alias being
    # matched. Kept explicit for clarity:
    _ = trig_lower  # silence linters; logic above already used line_lower

    return False


def _halt_literal_ok(line: str) -> bool:
    """Guard C — bare `HALT` literal discrimination.

    The bare token `HALT` only counts as a real HALT when:
      - it is the entire line (after stripping whitespace), OR
      - it appears in a clear status-emission form on a short line
        (less than 80 chars). Examples that pass:
          `HALT`
          `HALT.`
          `HALT: <reason>`
          `Status: HALTED.`
          `Status: HALT`

    Examples that fail (English noun in prose):
      `the HALT pattern in our spec`
      `do NOT auto-resolve. HALT and surface`
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Whole-line forms: `HALT`, `HALT.`, `HALT:` (with possible trailing reason).
    if re.fullmatch(r"HALT[.:]?", stripped, flags=re.IGNORECASE):
        return True

    # Status / Reason emissions that name HALT explicitly.
    if STATUS_EMISSION_RE.match(line):
        return True

    # Lines headed by `HALT` (e.g. `HALT: ambiguous sink architecture`).
    # Allow short lines only; long lines are almost certainly prose.
    if HALT_LITERAL_RE.match(stripped) and len(stripped) < 80:
        return True

    return False


# --- Directive-prose suppression (smoke-fix-2) -------------------------------
#
# Provenance: bmad-auto-v5-smoke-fix-2.md. The helper grep
# fallback runs against text the helper itself pasted into the spawned pane
# (the verbatim /goal directive). Smoke-runs 1 and 2 both surfaced false-
# positives where directive prose echoed in the pane tripped HALT triggers.
# Subtracting the pasted-directive content from grep input closes the class.


def _normalize_whitespace(s: str) -> str:
    """Collapse runs of whitespace to single spaces.

    Handles tmux terminal-width wrapping, which can insert wrap padding or
    split a long /goal line across multiple capture-pane lines.
    """
    return " ".join(s.split())


def is_directive_echo(capture_line: str, goal_lines: list[str]) -> bool:
    """Return True if ``capture_line`` is a verbatim echo of any
    ``goal_lines`` entry (after whitespace normalization).

    Comparison forms:
      - Exact match on whitespace-normalized strings.
      - Substring containment in either direction — handles tmux pane-width
        wrapping where a long /goal line splits into multiple capture-pane
        lines, or where a capture line concatenates fragments of two
        adjacent /goal lines.

    Empty / whitespace-only capture lines never count as echoes.
    """
    normalized = _normalize_whitespace(capture_line.strip())
    if not normalized:
        return False
    for goal_line in goal_lines:
        gnorm = _normalize_whitespace(goal_line.strip())
        if not gnorm:
            continue
        if gnorm == normalized:
            return True
        if normalized in gnorm or gnorm in normalized:
            return True
    return False


def _read_goal_lines(goal_file_path: str | None) -> list[str]:
    """Best-effort read of the /goal file used for the active spawn.

    Returns ``[]`` on any I/O error or a missing/empty path — callers
    treat that as "no suppression" (preserves pre-smoke-fix-2 behavior).
    """
    if not goal_file_path:
        return []
    try:
        path = pathlib.Path(goal_file_path)
        if not path.exists():
            return []
        return path.read_text().splitlines()
    except OSError as exc:
        log(f"goal-file read failed at {goal_file_path}: {exc}")
        return []


def _validate_sidecar(payload: dict, expected_story_id: str) -> tuple[bool, str]:
    """Return (is_valid, reason). Reason is empty when valid."""
    for field in SIDECAR_REQUIRED_FIELDS:
        if field not in payload:
            return False, f"missing required field '{field}'"
    if payload.get("storyId") != expected_story_id:
        return False, (
            f"storyId mismatch: sidecar={payload.get('storyId')!r} "
            f"expected={expected_story_id!r}"
        )
    return True, ""


def check_halt(
    session: str,
    story_id: str,
    sidecar_path: pathlib.Path | None,
    tail_lines: int = DEFAULT_TAIL_LINES,
    poll_number: int = 1,
    grep_warmup_polls: int = 0,
    goal_file_path: str | None = None,
    directives_file_path: str | None = None,
) -> dict:
    """Pure-logic HALT check. Returns the result dict (no I/O on stdout).

    Order of operations:
      1. Sidecar primary — if `sidecar_path` is provided AND parses AND
         passes schema/storyId validation, return immediately with
         `source: "sidecar"`.
      2. Warmup grace — when ``poll_number <= grep_warmup_polls``, skip
         the capture-pane grep step entirely (sidecar primary above still
         runs). Returns ``{"halt": false, "grep_suppressed": "warmup"}``.
         Lets the freshly-pasted /goal directive prose scroll off the
         pane before grep is trusted. See
         ``bmad-auto-v5-smoke-fix-1.md``.
      3. Grep fallback — capture the pane and walk the tail window. For
         each candidate line, first check ``is_directive_echo`` against
         the pasted /goal content (smoke-fix-2; skipped when
         ``goal_file_path`` is None or the file is unreadable), then
         apply the three structural guards, then match against the
         trigger set. On first surviving match, return `source: "grep"`.
      4. Otherwise, return `{"halt": false}`.

    Capture-pane failures (session gone, tmux missing) produce a non-
    fatal `{"halt": false, "error": "capture_pane_failed", ...}` result.

    Back-compat: the default ``grep_warmup_polls=0`` means no warmup
    grace (grep always runs); the default ``poll_number=1`` keeps the
    one-shot ``halt-check`` subcommand and existing tests behaving
    exactly as before. The default ``goal_file_path=None`` keeps
    directive-echo suppression off — pre-smoke-fix-2 semantics — so
    existing tests that do not pass a goal-file see no behavior change.

    Smoke-fix-3: ``directives_file_path`` adds a second pasted-content
    file to the suppression set (the directives-side message of the
    two-message spawn). When None, behavior is unchanged from
    smoke-fix-2. Provenance:
    bmad-auto-v5-smoke-fix-3.md.
    """
    # Step 1: sidecar primary.
    if sidecar_path is not None:
        payload = read_sidecar(sidecar_path)
        if payload is None:
            log(f"halt-check: sidecar absent/unreadable at {sidecar_path}")
        else:
            valid, reason = _validate_sidecar(payload, story_id)
            if valid:
                return {
                    "halt": True,
                    "class": payload["status"],
                    "reason": payload["reason"],
                    "source": "sidecar",
                    "files_affected": payload.get("files_affected", []),
                }
            log(f"halt-check: sidecar invalid ({reason}); falling through to grep")

    # Step 2: warmup grace — suppress grep entirely during early polls.
    if poll_number <= grep_warmup_polls:
        log(
            f"poll #{poll_number}: sidecar absent; grep suppressed "
            f"(warmup grace, {grep_warmup_polls} polls)."
        )
        return {"halt": False, "grep_suppressed": "warmup"}

    # Step 3: capture pane.
    capture = run_tmux(["capture-pane", "-p", "-S", "-200", "-t", session])
    if capture.returncode != 0:
        stderr = (capture.stderr or "").strip()
        log(f"halt-check: capture-pane failed (rc={capture.returncode}): {stderr}")
        return {
            "halt": False,
            "error": "capture_pane_failed",
            "stderr": stderr,
        }

    # Guard A — tail-window.
    tail = _apply_tail_window(capture.stdout, tail_lines)

    # Directive-prose suppression context (smoke-fix-2 + smoke-fix-3).
    # Loaded once per call so the per-line check is a list scan, not a
    # re-read. Smoke-fix-3 concatenates the directives-side message file
    # when the spawn used the two-message split.
    goal_lines = _read_goal_lines(goal_file_path)
    if directives_file_path:
        goal_lines = goal_lines + _read_goal_lines(directives_file_path)

    # Walk each surviving line, apply guards B & C, match triggers.
    for line in tail:
        # Smoke-fix-2: if this line is verbatim echo of pasted /goal
        # content, the helper itself put it on the pane — it is not a
        # HALT signal. Skip before any trigger / structural-guard work.
        if goal_lines and is_directive_echo(line, goal_lines):
            continue
        for class_name, aliases in HALT_TRIGGERS:
            for alias in aliases:
                if alias.lower() not in line.lower():
                    continue

                # Guard C — HALT literal discrimination. The `halt_literal`
                # class only counts via the structural form check; bypass
                # the standard prose-suppression flow.
                if class_name == "halt_literal":
                    if not _halt_literal_ok(line):
                        continue
                    return {
                        "halt": True,
                        "class": class_name,
                        "reason": line.strip(),
                        "source": "grep",
                    }

                # Guard B — prose-line suppression for non-HALT-literal
                # triggers.
                if _is_prose_suppressed(line, alias):
                    continue

                return {
                    "halt": True,
                    "class": class_name,
                    "reason": line.strip(),
                    "source": "grep",
                }

    return {"halt": False}


# --- Subcommand handlers -----------------------------------------------------


def cmd_spawn(args: argparse.Namespace) -> int:
    """Spawn a tmux-hosted Claude session and paste the goal directive.

    Pipeline (smoke-fix-3 two-message split when --directives-file given):
        1. tmux new-session -d -s <session> [ -c <cwd> ] claude --dangerously-skip-permissions
        2. Paste #1 — load-buffer / paste-buffer / send-keys C-m   (short /goal)
        3. sleep <inter-message-delay-seconds>                     (~3s default)
        4. Paste #2 — load-buffer / paste-buffer / send-keys C-m   (directives)
        5. Write spawn-sidecar recording both file paths

    Single-message back-compat: when --directives-file is omitted,
    steps 3 and 4 are skipped and the helper behaves exactly as before
    (pre-smoke-fix-3 single-paste flow).

    On any post-new-session failure, best-effort kill-session to clean
    up the half-spawned state before exiting EXIT_ERROR.
    """
    # Preflight: tmux on PATH
    if shutil.which("tmux") is None:
        print("tmux not found on PATH", file=sys.stderr)
        return EXIT_ERROR

    # Preflight: goal-file exists
    goal_path = pathlib.Path(args.goal_file)
    if not goal_path.exists():
        print(f"goal-file not found: {args.goal_file}", file=sys.stderr)
        return EXIT_NOT_FOUND

    # Preflight: directives-file (when set) exists. Same EXIT_NOT_FOUND
    # treatment as a missing goal-file.
    directives_path: pathlib.Path | None = None
    if args.directives_file:
        directives_path = pathlib.Path(args.directives_file)
        if not directives_path.exists():
            print(
                f"directives-file not found: {args.directives_file}",
                file=sys.stderr,
            )
            return EXIT_NOT_FOUND

    session_name = f"auto-K-{args.story_id}-{args.run_id}"
    log(
        f"spawn: session={session_name} goal-file={goal_path} "
        f"directives-file={directives_path} cwd={args.cwd}"
    )

    # Step 1: new-session
    new_session_args = ["new-session", "-d", "-s", session_name]
    if args.cwd:
        new_session_args.extend(["-c", args.cwd])
    new_session_args.extend(["claude", "--dangerously-skip-permissions"])
    result = run_tmux(new_session_args)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(
            f"tmux new-session failed: {stderr}" if stderr else "tmux new-session failed",
            file=sys.stderr,
        )
        return EXIT_ERROR

    # Post-new-session steps: paste the message(s). If any of these fail
    # the session is half-spawned — best-effort kill on the way out.
    def _cleanup_after_failure(step: str, completed: subprocess.CompletedProcess) -> int:
        stderr = (completed.stderr or "").strip()
        msg = f"tmux {step} failed"
        if stderr:
            msg = f"{msg}: {stderr}"
        print(msg, file=sys.stderr)
        kill_result = run_tmux(["kill-session", "-t", session_name])
        if kill_result.returncode != 0:
            log(f"cleanup kill-session also failed: {(kill_result.stderr or '').strip()}")
        return EXIT_ERROR

    paste_settle = max(0.0, float(
        getattr(args, "paste_to_submit_settle_seconds", DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS)
    ))

    def _paste_message(label: str, file_path: pathlib.Path) -> int | None:
        """Run load-buffer / paste-buffer / settle / send-keys for one message file.

        The brief sleep between paste-buffer and send-keys C-m is load-bearing
        when the pasted content is long enough for Claude Code v2 to fold it
        into `[Pasted text #N +M lines]` placeholders — without the settle
        delay, the C-m is swallowed by the TUI mid-render and the paste
        sits in the input box unsubmitted. See
        DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS for full provenance.

        Returns ``None`` on success or an EXIT_ERROR int on any step
        failure (the failing step has already killed the session).
        """
        r = run_tmux(["load-buffer", str(file_path)])
        if r.returncode != 0:
            return _cleanup_after_failure(f"load-buffer ({label})", r)
        r = run_tmux(["paste-buffer", "-t", session_name])
        if r.returncode != 0:
            return _cleanup_after_failure(f"paste-buffer ({label})", r)
        if paste_settle > 0:
            time.sleep(paste_settle)
        r = run_tmux(["send-keys", "-t", session_name, "C-m"])
        if r.returncode != 0:
            return _cleanup_after_failure(f"send-keys ({label})", r)
        return None

    # Wait for Claude to boot (welcome banner + workspace-trust prompt for
    # untrusted dirs), then send a single Enter to dismiss the trust prompt
    # (its default selection is "Yes, I trust this folder"). If the dir was
    # already trusted the Enter is a no-op on the idle prompt. Without this,
    # the first paste-buffer lands in an unstable input state and the
    # subsequent `C-m` fails to submit. See DEFAULT_CLAUDE_BOOT_WAIT_SECONDS
    # docstring for full provenance.
    # getattr fallbacks keep direct cmd_spawn(Namespace(...)) callers (unit
    # tests, library users) working without forcing them to set every new
    # field. CLI users still get the argparse defaults.
    boot_wait = max(0.0, float(
        getattr(args, "claude_boot_wait_seconds", DEFAULT_CLAUDE_BOOT_WAIT_SECONDS)
    ))
    if boot_wait > 0:
        log(f"spawn: sleeping {boot_wait}s for Claude to boot")
        time.sleep(boot_wait)
    r = run_tmux(["send-keys", "-t", session_name, "Enter"])
    if r.returncode != 0:
        return _cleanup_after_failure("send-keys (trust-prompt dismiss)", r)
    settle = max(0.0, float(
        getattr(args, "trust_prompt_settle_seconds", DEFAULT_TRUST_PROMPT_SETTLE_SECONDS)
    ))
    if settle > 0:
        log(f"spawn: sleeping {settle}s for trust prompt to settle")
        time.sleep(settle)

    # Paste #1 — short /goal (or the legacy single-message goal when
    # --directives-file is not provided).
    err = _paste_message("goal", goal_path)
    if err is not None:
        return err

    # Paste #2 — directives (smoke-fix-3 Workaround A). Sleep first to
    # let Claude Code accept the /goal before the next message arrives.
    if directives_path is not None:
        delay = max(0.0, float(args.inter_message_delay_seconds))
        if delay > 0:
            log(f"spawn: sleeping {delay}s between /goal and directives pastes")
            time.sleep(delay)
        err = _paste_message("directives", directives_path)
        if err is not None:
            return err

    spawned_at = datetime.now(timezone.utc).isoformat()

    # Smoke-fix-2: record the resolved goal-file path so cmd_monitor can
    # thread it into check_halt for directive-echo suppression. Best-
    # effort; failure here just degrades to the pre-smoke-fix-2 (no-
    # suppression) path. See bmad-auto-v5-smoke-fix-2.md.
    # Smoke-fix-3: also record directives_file_path (when set) so the
    # same suppression covers the second paste's verbatim content.
    spawn_sidecar = (
        _find_repo_root()
        / "_bmad-output"
        / ".run-state"
        / f"spawn-{args.story_id}-{args.run_id}.json"
    )
    spawn_payload = {
        "session_name": session_name,
        "spawned_at": spawned_at,
        "goal_file_path": str(goal_path.resolve()),
    }
    if directives_path is not None:
        spawn_payload["directives_file_path"] = str(directives_path.resolve())
    try:
        spawn_sidecar.parent.mkdir(parents=True, exist_ok=True)
        spawn_sidecar.write_text(json.dumps(spawn_payload, indent=2) + "\n")
    except OSError as exc:
        log(f"spawn-sidecar write failed at {spawn_sidecar}: {exc}")

    print(json.dumps({"session_name": session_name, "spawned_at": spawned_at}))
    return EXIT_OK


def _emit_result(result: dict) -> None:
    """Emit a single-line JSON result to stdout (monitor terminal output)."""
    print(json.dumps(result))


def _write_context_file(path: pathlib.Path, content: str) -> None:
    """Write a context file, creating parent dirs as needed. Best-effort."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    except OSError as exc:
        log(f"context-file write failed at {path}: {exc}")


def _kill_session(session: str) -> None:
    """Best-effort `tmux kill-session -t <session>`. Ignore non-zero."""
    result = run_tmux(["kill-session", "-t", session])
    if result.returncode != 0:
        log(
            f"kill-session non-zero (rc={result.returncode}): "
            f"{(result.stderr or '').strip()}"
        )


def _capture_pane(session: str, history: str = "-200") -> tuple[bool, str]:
    """Capture pane stdout. Returns (ok, text). `history` is the -S arg.

    Pass `"-"` for full scrollback (used for HALT/STALL context files);
    pass `"-200"` (default) for the rolling stall fingerprint.
    """
    capture = run_tmux(["capture-pane", "-p", "-S", history, "-t", session])
    if capture.returncode != 0:
        log(
            f"capture-pane failed (rc={capture.returncode}): "
            f"{(capture.stderr or '').strip()}"
        )
        return False, ""
    return True, capture.stdout


def cmd_monitor(args: argparse.Namespace) -> int:
    """Poll the spawned session until one of: completed / halted / stalled / timeout.

    Output contract:
      - stdout: single-line JSON on terminal state.
      - stderr: verbose log lines when --verbose is set.
      - exit code: 0 always (terminal state is data, not failure).

    Kill-on-terminal rules:
      - completed → kill session
      - halted    → kill session
      - stalled   → leave session running (operator may attach)
      - timeout   → leave session running (operator triage)
    """
    session = args.session
    story_id = args.story_id
    cadence = max(0, int(args.cadence_seconds))
    stall_warmup = max(1, int(args.stall_warmup_polls))
    stall_trip = max(1, int(args.stall_trip_polls))
    timeout_seconds = max(0, int(args.timeout_minutes)) * 60
    grep_warmup_polls = max(0, int(getattr(args, "grep_warmup_polls", 0)))
    suppress_directive_echo = not bool(
        getattr(args, "no_directive_echo_suppression", False)
    )

    sidecar_path = pathlib.Path(args.sidecar_path) if args.sidecar_path else None
    repo_root = _find_repo_root()

    # Smoke-fix-2: load goal-file path from spawn-sidecar so check_halt
    # can subtract pasted-directive content from grep input. Absent /
    # unreadable sidecar means no suppression (back to pre-smoke-fix-2
    # behavior). See bmad-auto-v5-smoke-fix-2.md.
    # Smoke-fix-3: also pick up directives_file_path so suppression covers
    # the second paste of the two-message spawn. See
    # bmad-auto-v5-smoke-fix-3.md.
    goal_file_path: str | None = None
    directives_file_path: str | None = None
    if suppress_directive_echo:
        spawn_sidecar = (
            repo_root
            / "_bmad-output"
            / ".run-state"
            / f"spawn-{story_id}-{args.run_id}.json"
        )
        spawn_payload = read_sidecar(spawn_sidecar)
        if spawn_payload and isinstance(spawn_payload.get("goal_file_path"), str):
            goal_file_path = spawn_payload["goal_file_path"]
        if spawn_payload and isinstance(spawn_payload.get("directives_file_path"), str):
            directives_file_path = spawn_payload["directives_file_path"]
        if not (goal_file_path or directives_file_path):
            log(
                f"monitor: spawn-sidecar absent/invalid at {spawn_sidecar}; "
                "directive-echo suppression will be a no-op this run."
            )

    halt_context_path = (
        repo_root
        / "_bmad-output"
        / ".run-state"
        / f"epic-K-story-{story_id}-halt-context.txt"
    )
    stall_context_path = (
        repo_root
        / "_bmad-output"
        / ".run-state"
        / f"epic-K-story-{story_id}-stall-context.txt"
    )

    log(
        f"monitor: session={session} story={story_id} cadence={cadence}s "
        f"warmup={stall_warmup} trip={stall_trip} "
        f"timeout={args.timeout_minutes}m sidecar={sidecar_path} "
        f"grep_warmup_polls={grep_warmup_polls} "
        f"directive_echo_suppression={suppress_directive_echo} "
        f"goal_file_path={goal_file_path} "
        f"directives_file_path={directives_file_path} repo_root={repo_root}"
    )

    start = time.time()
    # Initial wait — let the spawned Claude come up before we start polling.
    if cadence > 0:
        time.sleep(cadence)

    fingerprints: deque[str] = deque(maxlen=stall_trip)
    poll = 0

    while True:
        poll += 1
        elapsed = int(time.time() - start)

        # --- Completion check (authoritative) -------------------------
        sprint_status = read_sprint_status(repo_root)
        status = _story_status(sprint_status, story_id)
        if status == "done":
            log(f"poll #{poll}: sprint-status flipped to done at {elapsed}s")
            _kill_session(session)
            _emit_result(
                {
                    "final_state": "completed",
                    "exit_reason": "sprint_status_done",
                    "session_name": session,
                    "polls": poll,
                    "elapsed_seconds": elapsed,
                }
            )
            return EXIT_OK

        # --- HALT check (sidecar + grep) ------------------------------
        halt_result = check_halt(
            session=session,
            story_id=story_id,
            sidecar_path=sidecar_path,
            tail_lines=DEFAULT_TAIL_LINES,
            poll_number=poll,
            grep_warmup_polls=grep_warmup_polls,
            goal_file_path=goal_file_path,
            directives_file_path=directives_file_path,
        )
        if halt_result.get("halt"):
            ok, full_pane = _capture_pane(session, history="-")
            if ok:
                _write_context_file(halt_context_path, full_pane)
            _kill_session(session)
            payload: dict = {
                "final_state": "halted",
                "halt_class": halt_result.get("class"),
                "halt_reason": halt_result.get("reason"),
                "halt_source": halt_result.get("source"),
                "context_file": str(halt_context_path),
                "session_name": session,
                "polls": poll,
                "elapsed_seconds": elapsed,
            }
            if "files_affected" in halt_result:
                payload["files_affected"] = halt_result["files_affected"]
            log(
                f"poll #{poll}: HALT detected "
                f"({halt_result.get('source')}/{halt_result.get('class')}) "
                f"at {elapsed}s"
            )
            _emit_result(payload)
            return EXIT_OK

        # --- Stall fingerprint ---------------------------------------
        ok, pane_text = _capture_pane(session, history="-200")
        if ok:
            fingerprint = hashlib.sha1(pane_text.encode("utf-8")).hexdigest()
        else:
            # Capture failed — record a unique-per-poll sentinel so we
            # do not falsely accumulate identical fingerprints.
            fingerprint = f"capture-failed-{poll}"
        fingerprints.append(fingerprint)
        log(
            f"poll #{poll} fingerprint={fingerprint[:12]} elapsed={elapsed}s "
            f"history-len={len(fingerprints)}"
        )

        if (
            len(fingerprints) == stall_trip
            and poll >= stall_warmup
            and len(set(fingerprints)) == 1
        ):
            ok, full_pane = _capture_pane(session, history="-")
            if ok:
                _write_context_file(stall_context_path, full_pane)
            # NOTE: do NOT kill the session — operator may want to attach
            # and nudge per T1.4 picker notes.
            _emit_result(
                {
                    "final_state": "stalled",
                    "exit_reason": f"no_movement_{stall_trip}_polls",
                    "context_file": str(stall_context_path),
                    "session_name": session,
                    "polls": poll,
                    "elapsed_seconds": elapsed,
                }
            )
            return EXIT_OK

        # --- Timeout check -------------------------------------------
        if elapsed > timeout_seconds:
            # NOTE: do NOT kill the session — operator triage required.
            print(
                f"monitor timeout: session {session} still running after "
                f"{args.timeout_minutes}m — leaving for operator triage",
                file=sys.stderr,
            )
            _emit_result(
                {
                    "final_state": "timeout",
                    "exit_reason": f"exceeded_{args.timeout_minutes}m",
                    "session_name": session,
                    "polls": poll,
                    "elapsed_seconds": elapsed,
                }
            )
            return EXIT_OK

        # --- Sleep until next poll -----------------------------------
        if cadence > 0:
            time.sleep(cadence)


def cmd_halt_check(args: argparse.Namespace) -> int:
    """One-shot HALT check: sidecar-primary, then capture-pane grep + 3 guards.

    Thin CLI shim around `check_halt()`. T1.4's monitor subcommand calls
    `check_halt()` directly rather than shelling back out.

    Smoke-fix-3 T7 follow-up: now reads the spawn-state sidecar (when
    ``--run-id`` is provided) to thread ``goal_file_path`` +
    ``directives_file_path`` into ``check_halt``, matching ``cmd_monitor``'s
    directive-echo-suppression behavior. Without ``--run-id`` (or with
    ``--no-directive-echo-suppression``), suppression is a no-op — matches
    pre-fix behavior so existing callers don't regress.
    """
    sidecar_path = pathlib.Path(args.sidecar_path) if args.sidecar_path else None

    # Smoke-fix-3 T7 follow-up: thread directive-echo suppression through the
    # subcommand path, mirroring cmd_monitor's pattern. Optional --run-id
    # keeps the subcommand back-compat for callers that don't know the runId.
    goal_file_path: str | None = None
    directives_file_path: str | None = None
    suppress_directive_echo = not bool(
        getattr(args, "no_directive_echo_suppression", False)
    )
    run_id = getattr(args, "run_id", None)
    if suppress_directive_echo and run_id:
        repo_root = _find_repo_root()
        spawn_sidecar = (
            repo_root
            / "_bmad-output"
            / ".run-state"
            / f"spawn-{args.story_id}-{run_id}.json"
        )
        spawn_payload = read_sidecar(spawn_sidecar)
        if spawn_payload and isinstance(spawn_payload.get("goal_file_path"), str):
            goal_file_path = spawn_payload["goal_file_path"]
        if spawn_payload and isinstance(spawn_payload.get("directives_file_path"), str):
            directives_file_path = spawn_payload["directives_file_path"]
        if not (goal_file_path or directives_file_path):
            log(
                f"halt-check: spawn-sidecar absent/invalid at {spawn_sidecar}; "
                "directive-echo suppression will be a no-op."
            )

    result = check_halt(
        session=args.session,
        story_id=args.story_id,
        sidecar_path=sidecar_path,
        tail_lines=args.tail_lines,
        goal_file_path=goal_file_path,
        directives_file_path=directives_file_path,
    )
    print(json.dumps(result))
    return EXIT_OK


def cmd_derive_cadence(args: argparse.Namespace) -> int:
    """Map story-count to poll cadence in seconds (tiered).

    Output is a bare integer to stdout (no JSON wrapping) — SKILL.md consumes
    it as a shell variable via ``$(...)``. Zero / negative story counts are
    treated as a caller bug: there is nothing to poll, so we surface
    EXIT_ERROR with a stderr message rather than silently emitting a value.
    """
    count = args.story_count
    if count < 1:
        print(
            f"derive-cadence: --story-count must be >= 1 (got {count}); "
            "zero stories should not be polling.",
            file=sys.stderr,
        )
        return EXIT_ERROR
    cadence = CADENCE_HIGH_VOLUME
    for upper, seconds in CADENCE_TIERS:
        if count <= upper:
            cadence = seconds
            break
    print(cadence)
    return EXIT_OK


def cmd_kill(args: argparse.Namespace) -> int:
    """Idempotently kill a tmux session by name.

    Kill-on-already-dead is not an error — this is the common cleanup case
    (e.g. operator triage after `monitor` returned ``halted``). Only a
    missing ``tmux`` binary surfaces EXIT_ERROR; everything else exits 0.
    """
    if shutil.which("tmux") is None:
        print(
            "kill: tmux binary not found on PATH.",
            file=sys.stderr,
        )
        return EXIT_ERROR
    _kill_session(args.session)
    print(json.dumps({"killed": True, "session": args.session}))
    return EXIT_OK


# --- argparse wiring ---------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bmad-auto-helper.py",
        description=(
            "LLM-orchestrator helper for /bmad-auto. Owns spawn / monitor / "
            "halt-check / derive-cadence / kill. JSON to stdout, logs to "
            "stderr."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Emit verbose log lines to stderr.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="<subcommand>",
        required=True,
    )

    # spawn
    p_spawn = subparsers.add_parser(
        "spawn",
        help="Spawn a tmux-hosted Claude session for a story.",
    )
    p_spawn.add_argument("--story-id", required=True)
    p_spawn.add_argument("--run-id", required=True)
    p_spawn.add_argument("--goal-file", required=True)
    p_spawn.add_argument("--cwd", default=None)
    p_spawn.add_argument(
        "--directives-file",
        default=None,
        help=(
            "Optional path to a plain-prompt file pasted as a SECOND message "
            "~3s after the short /goal. When provided, the spawn flow pastes "
            "two messages: the short /goal payload first (must stay under "
            "Claude Code's 4000-char /goal ceiling), then this file verbatim "
            "as a regular user-turn prompt. This file is what carries the "
            "autonomous-mode directives. When omitted, the spawn flow falls "
            "back to a single-message paste (pre-smoke-fix-3 behavior). "
            "Provenance: bmad-auto-v5-smoke-fix-3.md."
        ),
    )
    p_spawn.add_argument(
        "--inter-message-delay-seconds",
        type=float,
        default=3.0,
        help=(
            "Seconds to sleep between the short /goal paste and the "
            "directives paste. Lets Claude Code accept the /goal before "
            "the second message arrives. Default 3.0 — matches the "
            "validated smoke-run-3 manual nudge timing. Ignored when "
            "--directives-file is not provided."
        ),
    )
    p_spawn.add_argument(
        "--claude-boot-wait-seconds",
        type=float,
        default=DEFAULT_CLAUDE_BOOT_WAIT_SECONDS,
        help=(
            "Seconds to sleep after `tmux new-session ... claude ...` to let "
            "Claude render its welcome banner + workspace-trust prompt before "
            "any input is sent. Default 10.0. Lower at your own risk — "
            "pasting during Claude's boot causes input-state corruption that "
            "leaves the per-story session stalled."
        ),
    )
    p_spawn.add_argument(
        "--trust-prompt-settle-seconds",
        type=float,
        default=DEFAULT_TRUST_PROMPT_SETTLE_SECONDS,
        help=(
            "Seconds to sleep after sending Enter to dismiss the workspace-"
            "trust prompt, before the first /goal paste. Default 3.0."
        ),
    )
    p_spawn.add_argument(
        "--paste-to-submit-settle-seconds",
        type=float,
        default=DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS,
        help=(
            "Seconds to sleep between `tmux paste-buffer` and the C-m submit "
            "send-keys. Required when Claude Code v2 folds the paste into "
            "`[Pasted text #N]` placeholders — without this settle delay the "
            "C-m is swallowed mid-render and the paste sits unsubmitted. "
            "Default 2.0."
        ),
    )
    p_spawn.set_defaults(func=cmd_spawn)

    # monitor
    p_monitor = subparsers.add_parser(
        "monitor",
        help="Poll the session until completed / halted / stalled / timeout.",
    )
    p_monitor.add_argument("--session", required=True)
    p_monitor.add_argument("--story-id", required=True)
    p_monitor.add_argument("--run-id", required=True)
    p_monitor.add_argument("--cadence-seconds", type=int, default=30)
    p_monitor.add_argument("--stall-warmup-polls", type=int, default=7)
    p_monitor.add_argument("--stall-trip-polls", type=int, default=3)
    p_monitor.add_argument("--timeout-minutes", type=int, default=60)
    p_monitor.add_argument("--sidecar-path", default=None)
    p_monitor.add_argument(
        "--grep-warmup-polls",
        type=int,
        default=2,
        help=(
            "Number of initial polls during which the capture-pane grep "
            "fallback is suppressed entirely (sidecar primary still runs "
            "every poll). Lets the freshly-pasted /goal directive prose "
            "scroll off the pane before grep is trusted. Default 2 "
            "(~90s at 45s cadence). Set to 0 to disable the warmup grace "
            "and run grep at poll #1. Provenance: "
            "bmad-auto-v5-smoke-fix-1.md."
        ),
    )
    p_monitor.add_argument(
        "--no-directive-echo-suppression",
        action="store_true",
        help=(
            "Opt out of directive-prose suppression. When the spawn-"
            "sidecar at "
            "_bmad-output/.run-state/spawn-<storyId>-<runId>.json "
            "is present, check_halt subtracts that /goal file's content "
            "from grep input so verbatim-echoed directive lines do not "
            "fire false-positives. Use this flag to reproduce the pre-"
            "smoke-fix-2 bug for tests/debugging. Provenance: "
            "bmad-auto-v5-smoke-fix-2.md."
        ),
    )
    p_monitor.set_defaults(func=cmd_monitor)

    # halt-check
    p_halt = subparsers.add_parser(
        "halt-check",
        help="One-shot HALT check (sidecar + capture-pane grep + 3 guards).",
    )
    p_halt.add_argument("--session", required=True)
    p_halt.add_argument("--story-id", required=True)
    p_halt.add_argument("--sidecar-path", default=None)
    p_halt.add_argument("--tail-lines", type=int, default=60)
    # Smoke-fix-3 T7 follow-up: optional --run-id lets halt-check read the
    # spawn-state sidecar and apply directive-echo suppression (mirrors
    # cmd_monitor). Optional for back-compat with pre-fix callers.
    p_halt.add_argument(
        "--run-id",
        default=None,
        help=(
            "Run identifier matching the spawn that produced the session. "
            "When provided, halt-check reads "
            "_bmad-output/.run-state/spawn-<story_id>-<run_id>.json and "
            "applies directive-echo suppression against the recorded "
            "goal_file_path + directives_file_path. Optional; omit for "
            "pre-smoke-fix-3 behavior (no suppression)."
        ),
    )
    p_halt.add_argument(
        "--no-directive-echo-suppression",
        action="store_true",
        help=(
            "Disable directive-echo suppression even when --run-id is "
            "provided. Mirrors cmd_monitor's flag of the same name."
        ),
    )
    p_halt.set_defaults(func=cmd_halt_check)

    # derive-cadence
    p_cadence = subparsers.add_parser(
        "derive-cadence",
        help="Map story-count to poll cadence in seconds (1-3=>45, 4-7=>30, 8+=>20).",
    )
    p_cadence.add_argument("--story-count", type=int, required=True)
    p_cadence.set_defaults(func=cmd_derive_cadence)

    # kill
    p_kill = subparsers.add_parser(
        "kill",
        help="Idempotently kill a tmux session by name.",
    )
    p_kill.add_argument("--session", required=True)
    p_kill.set_defaults(func=cmd_kill)

    return parser


def main() -> int:
    global _VERBOSE
    parser = build_parser()
    args = parser.parse_args()
    _VERBOSE = bool(getattr(args, "verbose", False))
    log(f"dispatching subcommand: {args.command}")
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
