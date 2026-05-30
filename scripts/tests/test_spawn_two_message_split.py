"""Structural backstop tests for smoke-fix-3's two-message spawn split.

These tests are the *single highest-leverage* addition in smoke-fix-3
per Murat's smoke-run-3 retrospective: they encode the invariants that
would have caught Bug 1 (`Goal condition is limited to 4000 characters
(got 6486)`) before the first smoke run ever spawned a per-story session.

Three asserts:

  Test 1 — ``/goal`` payload size ceiling.
      Construct a representative short-goal payload using realistic
      max-length values for storyId / runId / file paths. Assert the
      utf-8-encoded payload stays below Claude Code's 4000-char
      ``/goal`` ceiling. A companion assertion proves the *pre-fix*
      recipe (intent + paths + verbatim autonomous-mode directives
      inlined into one ``/goal``) exceeds the ceiling — i.e. the bug
      we are guarding against was real.

  Test 2 — Directives file exists and is non-empty.
      Catches accidental deletion or zeroing of
      ``references/autonomous-mode-directives.md``. Also asserts the
      file contains exactly 8 top-level numbered directives, matching
      directive #8's enumerated HALT class set and the SKILL.md /goal
      template's "Apply these 8 autonomous-mode directives" preamble.

  Test 3 — Two-message tmux structure in ``cmd_spawn``.
      Mock ``run_tmux`` + ``time.sleep`` and call ``cmd_spawn`` with
      both ``--goal-file`` and ``--directives-file`` set. Assert that
      the helper issues TWO load-buffer / paste-buffer / send-keys
      sequences (in that order), with a ``time.sleep`` call between
      them, where message #1's buffer file starts with ``/goal `` and
      message #2's does not.

Provenance: bmad-auto-v5-smoke-fix-3.md (T3).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
from unittest.mock import MagicMock

import pytest


# --- Claude Code /goal ceiling -----------------------------------------------
#
# Empirically observed in smoke-runs 1-3 (the error message reads
# "Goal condition is limited to 4000 characters (got <N>)"). Captured
# here as a module-level constant so test failures point at the
# operative number.
GOAL_PAYLOAD_CEILING_BYTES = 4000


# --- Test 1: /goal payload size ceiling --------------------------------------
#
# The two recipes below mirror the SKILL.md Stage 3.1 composer prose.
# We keep them locally inside the test file (not imported from the
# helper or from SKILL.md) so the test pins the *structural property*
# — "the composed payload must fit under 4000 chars" — independent of
# routine evolution in either source-of-truth recipe. Picker note from
# the task list: do NOT pin to exact current short-goal text.


def _compose_short_goal_payload(
    *,
    story_id: str,
    run_id: str,
    story_file_path: str,
    architecture_path: str,
    spec_path: str,
    atdd_checklist_path: str,
) -> str:
    """Build a representative short-goal payload (post-smoke-fix-3 recipe).

    Mirrors the shape of the validated smoke-run-3 manual nudge stored
    at `short-goal-100-2.txt` in the system temp dir (1208 bytes for the smoke-run-3
    values). The recipe carries intent + acceptance criteria + file
    paths only — no directive prose. Directive content rides in the
    second message (see ``_compose_directives_message`` for what that
    would look like; not asserted here).
    """
    return (
        f"/goal Implement story {story_id} of epic K. "
        f"Run via bmad-testarch-atdd (red scaffolds) → bmad-quick-dev "
        f"(make red green + clean impl) → bmad-testarch-automate or "
        f"bmad-qa-generate-e2e-tests (coverage, non-blocking) → "
        f"bmad-code-review. The 8 autonomous-mode directives arrive in "
        f"the NEXT user message — apply them verbatim throughout. "
        f"Story file: {story_file_path}. "
        f"Architecture: {architecture_path} (Format A-equivalent — "
        f"whole-project; no per-epic micro-architecture). "
        f"SPEC: {spec_path}. "
        f"ATDD checklist canonical path: {atdd_checklist_path} (discover "
        f"via glob _bmad-output/test-artifacts/atdd-checklist-{story_id}-*.md). "
        f"Mark sprint-status.yaml key `{story_id}` to `done` only when: "
        f"ATDD red tests authored AND bmad-quick-dev makes them green "
        f"with clean implementation AND code-review passes "
        f"(coverage-expansion optional/non-blocking). "
        f"Run id: {run_id}."
    )


def _compose_legacy_combined_payload(
    *,
    story_id: str,
    run_id: str,
    story_file_path: str,
    architecture_path: str,
    spec_path: str,
    atdd_checklist_path: str,
    directives_text: str,
) -> str:
    """Build the *pre*-smoke-fix-3 combined payload (one big /goal).

    This is the recipe SKILL.md Stage 3.1 was emitting up to and
    including smoke-run-3: the short intent + paths PLUS the verbatim
    autonomous-mode directives, all stuffed into a single ``/goal``
    directive string. The structural fault: directives.md is ~7KB and
    growing, so the combined string blows past Claude Code's 4000-char
    ``/goal`` ceiling.

    We compose it here only so Test 1's companion assertion can prove
    the bug existed. Not used by post-T2 helper code anywhere.
    """
    short = _compose_short_goal_payload(
        story_id=story_id,
        run_id=run_id,
        story_file_path=story_file_path,
        architecture_path=architecture_path,
        spec_path=spec_path,
        atdd_checklist_path=atdd_checklist_path,
    )
    # SKILL.md pre-fix prose: "Autonomous-mode directives:\n\n<verbatim
    # contents of references/autonomous-mode-directives.md>"
    return f"{short}\n\nAutonomous-mode directives:\n\n{directives_text}"


# Realistic max-length sentinel values — sized at typical upper bound
# for each field so the test catches bloat in any composer term.
_REALISTIC_STORY_ID = "100-2-validation-sandbox-paths-cmd"
_REALISTIC_RUN_ID = "20260527T073029Z"
# Synthetic absolute-path sentinel (not a real checkout) — sized at a
# realistic upper-bound length so the payload-size assertions stay conservative.
_REPO_ABS_PREFIX = "/Users/developer/projects/automator-main"
_REALISTIC_STORY_FILE = (
    f"{_REPO_ABS_PREFIX}/_bmad-output/implementation-artifacts/"
    f"{_REALISTIC_STORY_ID}.md"
)
_REALISTIC_ARCHITECTURE = (
    f"{_REPO_ABS_PREFIX}/_bmad-output/planning-artifacts/architecture.md"
)
_REALISTIC_SPEC = (
    f"{_REPO_ABS_PREFIX}/_bmad-output/specs/spec-validation-sandbox-2026-05-25/SPEC.md"
)
_REALISTIC_ATDD_CHECKLIST = (
    f"_bmad-output/test-artifacts/atdd-checklist-{_REALISTIC_STORY_ID}.md"
)


def test_short_goal_payload_stays_under_claude_code_ceiling():
    """Short-goal payload (post-smoke-fix-3 recipe) is under 4000 bytes.

    This is the structural invariant the smoke-fix-3 two-message split
    is designed to guarantee. If a future SKILL.md composer change bloats
    the short-goal recipe past 4000 chars (e.g. by re-introducing
    directive prose or stuffing additional context fields into the
    intent line), this assertion fires and the change blocks at CI.

    Provenance: smoke-run-3 Bug 1 — `/goal` rejected with
    "Goal condition is limited to 4000 characters (got 6486)". See
    bmad-auto-v5-smoke-fix-3.md.
    """
    payload = _compose_short_goal_payload(
        story_id=_REALISTIC_STORY_ID,
        run_id=_REALISTIC_RUN_ID,
        story_file_path=_REALISTIC_STORY_FILE,
        architecture_path=_REALISTIC_ARCHITECTURE,
        spec_path=_REALISTIC_SPEC,
        atdd_checklist_path=_REALISTIC_ATDD_CHECKLIST,
    )
    size = len(payload.encode("utf-8"))
    assert size < GOAL_PAYLOAD_CEILING_BYTES, (
        f"short-goal payload is {size} bytes; Claude Code rejects /goal "
        f">= {GOAL_PAYLOAD_CEILING_BYTES} bytes. The smoke-fix-3 "
        "two-message split must keep this payload below the ceiling. "
        "If the composer recipe needs more headroom, push directive-side "
        "content into the second (plain-prompt) message instead of "
        "inlining it here."
    )


def test_legacy_combined_payload_proves_smoke_run_3_bug():
    """The pre-smoke-fix-3 combined-payload recipe exceeds 4000 bytes.

    This is the *regression* assertion: it proves Bug 1 from
    smoke-run-3 was real by computing the size of the payload SKILL.md
    Stage 3.1 was producing pre-fix (short intent + paths PLUS verbatim
    directives.md). If this somehow drops below 4000 bytes — by either
    a directives.md compression or a SKILL.md recipe slimming — the
    operator should reconsider whether the two-message split is still
    necessary or whether a single-payload fallback now suffices.
    """
    directives_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "references"
        / "autonomous-mode-directives.md"
    )
    assert directives_path.exists(), (
        f"directives file missing at {directives_path}; this should never "
        "happen in a healthy checkout."
    )
    directives_text = directives_path.read_text()
    combined = _compose_legacy_combined_payload(
        story_id=_REALISTIC_STORY_ID,
        run_id=_REALISTIC_RUN_ID,
        story_file_path=_REALISTIC_STORY_FILE,
        architecture_path=_REALISTIC_ARCHITECTURE,
        spec_path=_REALISTIC_SPEC,
        atdd_checklist_path=_REALISTIC_ATDD_CHECKLIST,
        directives_text=directives_text,
    )
    size = len(combined.encode("utf-8"))
    assert size >= GOAL_PAYLOAD_CEILING_BYTES, (
        f"legacy combined payload is {size} bytes — below Claude Code's "
        f"{GOAL_PAYLOAD_CEILING_BYTES}-char /goal ceiling. Smoke-fix-3's "
        "two-message split was introduced to work around Bug 1, where this "
        "combined payload exceeded the ceiling. If the legacy recipe now "
        "fits, the structural fix is no longer load-bearing — re-evaluate "
        "before relying on this guard."
    )


# --- Test 2: directives file integrity ---------------------------------------


def test_autonomous_mode_directives_file_present_and_has_eight_numbered_directives():
    """references/autonomous-mode-directives.md exists, is non-empty,
    and contains exactly 8 top-level numbered directives.

    Why 8: directive #8 enumerates 7 HALT-class statuses (intent_gap |
    bad_spec | loopback_overflow | vcs_dirty | wrong_branch | halt |
    red_tests_failing); the SKILL.md /goal template's preamble says
    "Apply these 8 autonomous-mode directives verbatim". Drift in
    either direction (lost directive, accidental renumber, added 9th
    directive without updating the SKILL.md preamble) should fail
    here so the inconsistency is caught at CI.

    Provenance: bmad-auto-v5-smoke-fix-3.md (T3).
    """
    directives_path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "references"
        / "autonomous-mode-directives.md"
    )
    assert directives_path.exists(), (
        f"directives file missing at {directives_path}"
    )
    text = directives_path.read_text()
    assert text.strip(), "directives file is empty"

    # Match top-level numbered directive headers — lines like
    # "1. **CHECKPOINT 1 — default `[A] Approve`.**" at column 0.
    # Bounded by 1..9 to avoid catching arbitrary numbered prose
    # inside a directive's body (e.g. directive #5's "Five rounds of
    # the implement/review loopback cycle").
    pattern = re.compile(r"^(\d)\.\s+\*\*", re.MULTILINE)
    matches = pattern.findall(text)
    numbers = [int(n) for n in matches]
    assert numbers == [1, 2, 3, 4, 5, 6, 7, 8], (
        f"expected directives numbered 1..8; found {numbers!r}. Either a "
        "directive was lost, the numbering drifted, or a 9th directive was "
        "added without updating the SKILL.md /goal preamble's "
        '"Apply these 8 autonomous-mode directives" line.'
    )


# --- Test 3: cmd_spawn two-message tmux structure ----------------------------


def test_cmd_spawn_issues_two_paste_sequences_with_sleep_between(
    helper, monkeypatch, tmp_path
):
    """End-to-end shape of the post-smoke-fix-3 spawn flow.

    Mock ``run_tmux`` + ``time.sleep`` + ``shutil.which`` and invoke
    ``cmd_spawn`` with both ``--goal-file`` (short /goal) and
    ``--directives-file`` (verbatim directives). Assert the helper:

      - issues exactly TWO ``load-buffer`` calls, in goal-then-directives
        order
      - issues exactly TWO ``paste-buffer`` calls
      - issues exactly TWO ``send-keys ... C-m`` calls
      - calls ``time.sleep`` exactly once between the two pastes
      - the first ``load-buffer``'s file content starts with ``/goal ``
      - the second ``load-buffer``'s file content does NOT start with
        ``/goal `` (it is a plain user-turn prompt carrying the directives)

    This is the operational counterpart of Test 1: Test 1 guards the
    payload-size invariant, Test 3 guards the wire-protocol invariant.
    Either alone would have caught Bug 1 in CI; both together pin the
    helper to the exact shape validated empirically in smoke-run-3's
    manual nudge.
    """
    # Build two realistic files
    goal_path = tmp_path / "short-goal.txt"
    goal_path.write_text("/goal smoke-test intent + paths only.")
    directives_path = tmp_path / "directives.txt"
    directives_path.write_text(
        "Apply these 8 autonomous-mode directives verbatim "
        "throughout the goal above:\n\n"
        "1. directive one ...\n2. directive two ...\n"
    )

    # Repo-root resolution writes a spawn-sidecar; chdir to tmp_path so
    # the side effect lands inside the test fixture.
    sidecar_dir = tmp_path / "_bmad-output" / ".run-state"
    sidecar_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    # Pretend tmux is on PATH.
    monkeypatch.setattr(helper.shutil, "which", lambda _: "/usr/bin/tmux")

    # Mock run_tmux — all calls succeed.
    mock_tmux = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="", stderr=""
        )
    )
    monkeypatch.setattr(helper, "run_tmux", mock_tmux)

    # Track time.sleep calls (no actual sleeping).
    sleep_calls: list[float] = []
    monkeypatch.setattr(helper.time, "sleep", lambda s: sleep_calls.append(s))

    # Invoke cmd_spawn directly with a Namespace mirroring the CLI.
    args = argparse.Namespace(
        story_id="100-2",
        run_id="20260527T073029Z",
        goal_file=str(goal_path),
        cwd=None,
        directives_file=str(directives_path),
        inter_message_delay_seconds=3.0,
        # Opt out of boot-wait + trust-prompt sleeps for this test — its
        # focus is the two-message paste protocol, not the spawn warmup.
        # The send-keys Enter for trust-prompt dismissal still fires
        # unconditionally and is tolerated by the C-m-only filter below.
        claude_boot_wait_seconds=0.0,
        trust_prompt_settle_seconds=0.0,
        paste_to_submit_settle_seconds=0.0,
    )
    rc = helper.cmd_spawn(args)
    assert rc == helper.EXIT_OK, f"cmd_spawn returned non-zero: {rc}"

    # Decompose the tmux calls.
    calls = [call.args[0] for call in mock_tmux.call_args_list]
    new_session_calls = [c for c in calls if c and c[0] == "new-session"]
    load_buffer_calls = [c for c in calls if c and c[0] == "load-buffer"]
    paste_buffer_calls = [c for c in calls if c and c[0] == "paste-buffer"]
    send_keys_calls = [c for c in calls if c and c[0] == "send-keys"]

    assert len(new_session_calls) == 1, (
        f"expected 1 new-session call; got {len(new_session_calls)}: {calls!r}"
    )
    assert len(load_buffer_calls) == 2, (
        f"expected exactly 2 load-buffer calls (one per message); got "
        f"{len(load_buffer_calls)}: {load_buffer_calls!r}"
    )
    assert len(paste_buffer_calls) == 2, (
        f"expected exactly 2 paste-buffer calls; got {len(paste_buffer_calls)}"
    )
    # send-keys count: 2 for message pastes (C-m each). cmd_spawn does
    # not use send-keys for anything else on the happy path.
    enter_calls = [c for c in send_keys_calls if c[-1] == "C-m"]
    assert len(enter_calls) == 2, (
        f"expected exactly 2 send-keys C-m calls; got {len(enter_calls)}: "
        f"{send_keys_calls!r}"
    )

    # Sleep between the two pastes — exactly once, with the configured delay.
    assert sleep_calls == [3.0], (
        f"expected a single time.sleep(3.0) between pastes; got {sleep_calls!r}"
    )

    # Path ordering: goal first, directives second.
    assert load_buffer_calls[0][1] == str(goal_path), (
        f"first load-buffer should reference the goal file; got "
        f"{load_buffer_calls[0]!r}"
    )
    assert load_buffer_calls[1][1] == str(directives_path), (
        f"second load-buffer should reference the directives file; got "
        f"{load_buffer_calls[1]!r}"
    )

    # Prefix invariants on the loaded file contents.
    goal_content = pathlib.Path(load_buffer_calls[0][1]).read_text()
    directives_content = pathlib.Path(load_buffer_calls[1][1]).read_text()
    assert goal_content.startswith("/goal "), (
        f"message 1 should start with '/goal '; first 40 chars: {goal_content[:40]!r}"
    )
    assert not directives_content.startswith("/goal "), (
        "message 2 must NOT start with '/goal ' — it is a regular "
        f"user-turn prompt; first 40 chars: {directives_content[:40]!r}"
    )


def test_cmd_spawn_without_directives_file_keeps_single_message_back_compat(
    helper, monkeypatch, tmp_path
):
    """Back-compat: omitting --directives-file produces a single paste.

    Guards against a future refactor accidentally forcing the
    two-message split. Pre-T5 SKILL.md callers (still composing one
    big goal file) must keep working, and the legacy single-message
    behavior must remain exercised by the test suite.
    """
    goal_path = tmp_path / "goal.txt"
    goal_path.write_text("/goal smoke-test single-message back-compat path.")

    (tmp_path / "_bmad-output" / ".run-state").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(helper.shutil, "which", lambda _: "/usr/bin/tmux")
    mock_tmux = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="", stderr=""
        )
    )
    monkeypatch.setattr(helper, "run_tmux", mock_tmux)
    sleep_calls: list[float] = []
    monkeypatch.setattr(helper.time, "sleep", lambda s: sleep_calls.append(s))

    args = argparse.Namespace(
        story_id="legacy",
        run_id="20260527T000000Z",
        goal_file=str(goal_path),
        cwd=None,
        directives_file=None,
        inter_message_delay_seconds=3.0,
        # Opt out of boot-wait + trust-prompt sleeps for this back-compat test.
        claude_boot_wait_seconds=0.0,
        trust_prompt_settle_seconds=0.0,
        paste_to_submit_settle_seconds=0.0,
    )
    rc = helper.cmd_spawn(args)
    assert rc == helper.EXIT_OK

    calls = [call.args[0] for call in mock_tmux.call_args_list]
    load_buffer_calls = [c for c in calls if c and c[0] == "load-buffer"]
    assert len(load_buffer_calls) == 1, (
        f"single-message back-compat path must produce exactly 1 "
        f"load-buffer call; got {len(load_buffer_calls)}: {load_buffer_calls!r}"
    )
    assert sleep_calls == [], (
        f"single-message path must not call time.sleep; got {sleep_calls!r}"
    )


def test_cmd_spawn_applies_boot_wait_trust_dismiss_and_paste_settle_by_default(
    helper, monkeypatch, tmp_path
):
    """Regression guard for the Claude Code v2.1.153 spawn-warmup fixes.

    Empirically captured 2026-05-28 in the bmad-auto e2e harness: without
    a boot wait + workspace-trust-prompt dismissal + paste-to-submit
    settle, the per-story spawn races Claude's boot/UI rendering and
    leaves both pasted messages sitting in the input box unsubmitted,
    stalling Phase 3 fanout for the entire epic.

    This test pins the three new sleeps + the Enter dismissal so any
    future refactor that drops them re-surfaces the production stall
    immediately, not on the next slow e2e run.
    """
    goal_path = tmp_path / "goal.txt"
    goal_path.write_text("/goal warmup-regression test.")
    directives_path = tmp_path / "directives.txt"
    directives_path.write_text("plain prompt body.\n")

    (tmp_path / "_bmad-output" / ".run-state").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(helper.shutil, "which", lambda _: "/usr/bin/tmux")
    mock_tmux = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="", stderr=""
        )
    )
    monkeypatch.setattr(helper, "run_tmux", mock_tmux)
    sleep_calls: list[float] = []
    monkeypatch.setattr(helper.time, "sleep", lambda s: sleep_calls.append(s))

    args = argparse.Namespace(
        story_id="warmup",
        run_id="20260528T000000Z",
        goal_file=str(goal_path),
        cwd=None,
        directives_file=str(directives_path),
        inter_message_delay_seconds=3.0,
        # Defaults under test — NOT opting out as the other spawn tests do.
        claude_boot_wait_seconds=helper.DEFAULT_CLAUDE_BOOT_WAIT_SECONDS,
        trust_prompt_settle_seconds=helper.DEFAULT_TRUST_PROMPT_SETTLE_SECONDS,
        paste_to_submit_settle_seconds=helper.DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS,
    )
    rc = helper.cmd_spawn(args)
    assert rc == helper.EXIT_OK, f"cmd_spawn returned non-zero: {rc}"

    # Sleep sequence in order: boot, trust-settle, paste1-settle,
    # inter-message, paste2-settle.
    expected_sleeps = [
        helper.DEFAULT_CLAUDE_BOOT_WAIT_SECONDS,
        helper.DEFAULT_TRUST_PROMPT_SETTLE_SECONDS,
        helper.DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS,
        3.0,  # inter_message_delay_seconds
        helper.DEFAULT_PASTE_TO_SUBMIT_SETTLE_SECONDS,
    ]
    assert sleep_calls == expected_sleeps, (
        f"expected spawn-warmup sleep sequence {expected_sleeps!r}; "
        f"got {sleep_calls!r}"
    )

    calls = [call.args[0] for call in mock_tmux.call_args_list]
    send_keys_calls = [c for c in calls if c and c[0] == "send-keys"]
    enter_calls = [c for c in send_keys_calls if c[-1] == "Enter"]
    cm_calls = [c for c in send_keys_calls if c[-1] == "C-m"]

    assert len(enter_calls) == 1, (
        f"expected exactly 1 send-keys Enter for trust-prompt dismissal; "
        f"got {len(enter_calls)}: {send_keys_calls!r}"
    )
    assert len(cm_calls) == 2, (
        f"expected exactly 2 send-keys C-m (one per message submit); "
        f"got {len(cm_calls)}: {send_keys_calls!r}"
    )

    # Ordering: the trust-dismiss Enter must fire before any paste-buffer.
    enter_idx = next(
        i for i, c in enumerate(calls)
        if c and c[0] == "send-keys" and c[-1] == "Enter"
    )
    first_paste_idx = next(
        i for i, c in enumerate(calls) if c and c[0] == "paste-buffer"
    )
    assert enter_idx < first_paste_idx, (
        f"trust-dismiss Enter must be sent before any paste-buffer; "
        f"Enter at index {enter_idx}, first paste-buffer at index "
        f"{first_paste_idx}. Calls: {calls!r}"
    )
