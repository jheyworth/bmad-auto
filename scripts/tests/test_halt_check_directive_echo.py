"""Regression tests for the v5 smoke-fix-2 directive-prose suppression.

Provenance: ``bmad-auto-v5-smoke-fix-2.md`` (G1). The
fixtures are verbatim captures from smoke-run-2 (runId
``20260527T065303Z``), which HALTed in Phase 3 Stage 3.4 poll #3 on a
``red_tests_failing`` false-positive — the helper grep matched the
verbatim text of autonomous-mode-directive #8 that the helper itself
had pasted into the spawned session's ``/goal`` condition.

Same root cause as smoke-fix-1 (`loopback_overflow` echo of directive
#5 at poll #1). Smoke-fix-1's warmup grace pushed the bug from poll #1
to poll #3 but did not eliminate the class. Smoke-fix-2 implements
the architectural fix: subtract the pasted-directive content from the
grep input.

Two tests:
  - Test 1 (regression baseline) — replays the failure with NO
    goal-file context. Asserts the existing bug fires. Documents the
    pre-fix behavior so any future change that simultaneously breaks
    the structural guards AND solves directive-echo gets caught.
  - Test 2 (fix contract) — replays the same pane WITH the goal-file
    context. Asserts the fix suppresses the directive echo and
    returns halt=False. Fails (TypeError) until G2 ships the
    ``goal_file_path`` kwarg on ``check_halt``.
"""

from __future__ import annotations

import subprocess


def _stub_capture(helper, monkeypatch, text: str, returncode: int = 0, stderr: str = ""):
    """Make ``helper.run_tmux`` return a CompletedProcess with given stdout."""

    def fake(args):
        return subprocess.CompletedProcess(
            args=args, returncode=returncode, stdout=text, stderr=stderr
        )

    monkeypatch.setattr(helper, "run_tmux", fake)


def test_directive_echo_without_goal_context_documents_existing_bug(
    helper, fixtures_dir, monkeypatch
):
    """Regression baseline: with NO goal_file context, the verbatim pane
    capture from smoke-run-2 poll #3 must still trip the documented bug
    — grep matches directive #8's ``red tests still failing`` prose.

    This pin protects against an accidental future change that removes
    the structural guards AND fixes directive-echo: without this
    baseline the guard-loss would go silent.
    """
    fixture = fixtures_dir / "halt-context-100-2-directive-echo-poll3.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())
    result = helper.check_halt("sess", "100-2", None)
    assert result["halt"] is True
    assert result["class"] == "red_tests_failing"
    assert result["source"] == "grep"


def test_directive_echo_with_goal_context_is_suppressed(
    helper, fixtures_dir, monkeypatch
):
    """Fix contract: passing the goal-file path lets ``check_halt``
    recognize that the matching line is verbatim directive prose the
    helper itself pasted, and suppress the false-positive.

    Fails (TypeError) until G2 wires ``goal_file_path`` into
    ``check_halt``. After G2 lands the result must be
    ``{"halt": False, ...}`` — there is no real HALT signal in the
    smoke-run-2 fixture.
    """
    fixture = fixtures_dir / "halt-context-100-2-directive-echo-poll3.txt"
    goal_file = fixtures_dir / "goal-100-2.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())
    result = helper.check_halt(
        "sess",
        "100-2",
        None,
        goal_file_path=str(goal_file),
    )
    assert result["halt"] is False, (
        "directive-echo suppression should fire on the smoke-run-2 pane "
        f"when the goal-file context is provided; check_halt returned {result!r}"
    )
