"""Unit tests for the capture-pane grep fallback in ``check_halt``.

Calls the library function directly (Option A) with ``sidecar_path=None``,
patching ``helper.run_tmux`` to return the contents of each fixture as the
capture-pane body.

Coverage:
  - 7 positive fixtures (1 each per HALT class) → expect halt=True.
  - 5+ negative fixtures → expected behavior split between:
      * Clean negatives: the heuristic correctly returns halt=False.
      * Documented heuristic limitations (per
        ``../../test-fixtures/halt-detection/README.md``): the
        heuristic fires HALT because substring matching cannot resolve
        negation semantics ("...is now resolved", quoted prose, etc).
        Tests assert the CURRENT (limitation) behavior with a
        ``# Documented heuristic limitation`` comment.

The negatives in the "documented false-positive" bucket are still
load-bearing — they pin the current behavior so a future heuristic
upgrade has a baseline to diff against.
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


# --- Positive fixtures --------------------------------------------------------


def test_trigger_intent_gap(helper, fixtures_dir, monkeypatch):
    _stub_capture(helper, monkeypatch, (fixtures_dir / "trigger-intent-gap.txt").read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "intent_gap"
    assert result["source"] == "grep"


def test_trigger_bad_spec(helper, fixtures_dir, monkeypatch):
    _stub_capture(helper, monkeypatch, (fixtures_dir / "trigger-bad-spec.txt").read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "bad_spec"
    assert result["source"] == "grep"


def test_trigger_vcs_dirty(helper, fixtures_dir, monkeypatch):
    _stub_capture(helper, monkeypatch, (fixtures_dir / "trigger-vcs-dirty.txt").read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "vcs_dirty"
    assert result["source"] == "grep"


def test_trigger_wrong_branch(helper, fixtures_dir, monkeypatch):
    _stub_capture(helper, monkeypatch, (fixtures_dir / "trigger-wrong-branch.txt").read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "wrong_branch"
    assert result["source"] == "grep"


def test_trigger_loopback_overflow(helper, fixtures_dir, monkeypatch):
    _stub_capture(
        helper, monkeypatch, (fixtures_dir / "trigger-loopback-overflow.txt").read_text()
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "loopback_overflow"
    assert result["source"] == "grep"


def test_trigger_explicit_halt(helper, fixtures_dir, monkeypatch):
    _stub_capture(helper, monkeypatch, (fixtures_dir / "trigger-explicit-halt.txt").read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "halt_literal"
    assert result["source"] == "grep"


def test_trigger_red_tests_failing(helper, fixtures_dir, monkeypatch):
    _stub_capture(
        helper, monkeypatch, (fixtures_dir / "trigger-red-tests-failing.txt").read_text()
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True
    assert result["class"] == "red_tests_failing"
    assert result["source"] == "grep"


# --- Clean negative fixtures --------------------------------------------------


def test_negative_clean_progress(helper, fixtures_dir, monkeypatch):
    """Vanilla healthy completion. No trigger substrings. Must be NOT-HALT."""
    _stub_capture(helper, monkeypatch, (fixtures_dir / "negative-clean-progress.txt").read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is False


def test_negative_loopback_count_2(helper, fixtures_dir, monkeypatch):
    """Iteration 2 of N — phrasing deliberately avoids the published aliases."""
    _stub_capture(
        helper, monkeypatch, (fixtures_dir / "negative-loopback-count-2.txt").read_text()
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is False


def test_negative_halt_in_prompt_scrollback(helper, fixtures_dir, monkeypatch):
    """D11v4 canonical case — tail-window + prose-suppression guards close
    the Deviation #7 false-positive class introduced by /goal prompt prose
    in the buffer top. Must be NOT-HALT under the tuned guards.
    """
    _stub_capture(
        helper,
        monkeypatch,
        (fixtures_dir / "negative-halt-in-prompt-scrollback.txt").read_text(),
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is False


# --- Documented heuristic limitations ----------------------------------------
#
# Per ../../test-fixtures/halt-detection/README.md, the following
# fixtures are EXPECTED to false-positive under the current substring-with-
# 3-guards heuristic. The README documents each as a "Classification under
# the rule as written: HALT (false-positive)" while a human operator
# would classify NOT-HALT. We pin the current behavior here so future
# heuristic upgrades have a regression baseline.


def test_negative_branch_discussion_documented_false_positive(
    helper, fixtures_dir, monkeypatch
):
    # Documented heuristic limitation per halt-detection/README.md — the
    # "this is an aside ... not a HALT condition" prose contains the bare
    # substring "intent gap" in unrelated text, and the matcher cannot
    # resolve the negation semantics.
    _stub_capture(
        helper, monkeypatch, (fixtures_dir / "negative-branch-discussion.txt").read_text()
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True  # documented limitation: not a real HALT


def test_negative_intent_gap_resolved_documented_false_positive(
    helper, fixtures_dir, monkeypatch
):
    # Documented heuristic limitation per halt-detection/README.md — guards
    # can't resolve negation ("the intent_gap is now resolved").
    _stub_capture(
        helper, monkeypatch, (fixtures_dir / "negative-intent-gap-resolved.txt").read_text()
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True  # documented limitation


def test_negative_mention_of_halt_in_spec_documented_false_positive(
    helper, fixtures_dir, monkeypatch
):
    # Documented heuristic limitation per halt-detection/README.md — every
    # trigger substring appears multiple times in a docs-only spec; the
    # matcher cannot recognize that the story spec itself is *about*
    # HALT semantics.
    _stub_capture(
        helper,
        monkeypatch,
        (fixtures_dir / "negative-mention-of-halt-in-spec.txt").read_text(),
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True  # documented limitation


def test_negative_red_tests_discussion_documented_false_positive(
    helper, fixtures_dir, monkeypatch
):
    # Documented heuristic limitation per halt-detection/README.md — v4
    # red-tests trigger substrings appear inside methodology prose; the
    # tuned guards suppress most matches but a residual line still trips.
    _stub_capture(
        helper,
        monkeypatch,
        (fixtures_dir / "negative-red-tests-discussion.txt").read_text(),
    )
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True  # documented limitation


# --- Smoke-fix-1 regression: warmup grace suppresses grep --------------------
#
# Provenance: bmad-auto-v5-smoke-fix-1.md (F1 red test for
# the 2026-05-27 v5 smoke run, runId 20260527T044517Z). The smoke run
# HALTed in Phase 3 Stage 3.4 poll #1 on a `loopback_overflow` false-
# positive — the fresh per-story pane was dominated by the pasted /goal
# directive prose, and the structural guards did not suppress directive 8's
# bare `loopback overflow` substring (it appears in an enumeration where
# its siblings `intent_gap` / `bad_spec` are backticked but `loopback
# overflow` itself is not, so guard B's quoted-form check does not fire).
#
# The fix is a warmup grace period: during the first N polls of a
# session's lifetime the monitor passes a signal through to check_halt
# that suppresses the grep step entirely (sidecar primary still runs).
# By the time grep is trusted (poll N+1 onward), the directive prose has
# scrolled off the pane.


def test_halt_check_grep_ignores_pasted_directive_during_warmup(
    helper, fixtures_dir, monkeypatch
):
    """Poll #1 within a 2-poll warmup window: grep is suppressed, so
    the pasted-directive pane must NOT classify halt.

    Under current (pre-F2) code this test fails — `check_halt` does not
    accept the warmup kwargs, so the call raises TypeError. Under the
    F2 fix the kwargs exist and skip the grep step when
    ``poll_number <= grep_warmup_polls``.
    """
    fixture = fixtures_dir / "halt-context-100-2-directive-prose.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())
    result = helper.check_halt(
        "sess",
        "story",
        None,
        poll_number=1,
        grep_warmup_polls=2,
    )
    assert result["halt"] is False, (
        "warmup grace should suppress grep on the pasted-directive pane; "
        f"check_halt returned {result!r}"
    )


def test_halt_check_grep_directive_prose_post_warmup_documented_limitation(
    helper, fixtures_dir, monkeypatch
):
    """Pins the post-warmup behavior so a future structural-guard upgrade
    has a diff baseline. After the warmup window expires (poll N+1
    onward) grep runs as before; if the directive prose is somehow still
    in the pane, the documented false-positive still fires.

    The fix-task-list explicitly defers approach (c) (tighter structural
    guards) unless approaches (a)+(b) prove insufficient — so this stays
    a documented limitation, not a defect to fix here.
    """
    fixture = fixtures_dir / "halt-context-100-2-directive-prose.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())
    result = helper.check_halt("sess", "story", None)
    assert result["halt"] is True  # documented limitation
    assert result["class"] == "loopback_overflow"
