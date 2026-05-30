"""Unit tests for the sidecar-primary path of ``check_halt``.

Calls the library function directly (Option A) — no subprocess. Each
test points ``sidecar_path`` at one of the existing fixtures in
``../../test-fixtures/halt-detection/`` and asserts the
contracted return shape (halt / class / source).

Fixture → expected story-id / status mapping (from inspection):
    sidecar-intent-gap.json        → K-3-tiered-window / intent_gap
    sidecar-bad-spec.json          → 5-2-export-csv  / bad_spec
    sidecar-red-tests-failing.json → 4-3-quota-reset / red_tests_failing
    negative-sidecar-malformed.json → truncated; should NOT parse → fall through
"""

from __future__ import annotations

import subprocess


def _stub_capture_pane_empty(helper, monkeypatch):
    """Patch ``run_tmux`` to return a successful empty capture.

    Used when the sidecar fall-through path needs a deterministic
    capture-pane response (no triggers).
    """

    def fake(args):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(helper, "run_tmux", fake)


def test_sidecar_intent_gap_fires_halt(helper, fixtures_dir):
    """sidecar-intent-gap.json with matching storyId → halt via sidecar."""
    sidecar = fixtures_dir / "sidecar-intent-gap.json"
    result = helper.check_halt(
        session="ignored",
        story_id="K-3-tiered-window",
        sidecar_path=sidecar,
    )
    assert result["halt"] is True
    assert result["class"] == "intent_gap"
    assert result["source"] == "sidecar"
    assert "files_affected" in result
    assert isinstance(result["files_affected"], list)


def test_sidecar_bad_spec_fires_halt(helper, fixtures_dir):
    """sidecar-bad-spec.json with matching storyId → halt via sidecar."""
    sidecar = fixtures_dir / "sidecar-bad-spec.json"
    result = helper.check_halt(
        session="ignored",
        story_id="5-2-export-csv",
        sidecar_path=sidecar,
    )
    assert result["halt"] is True
    assert result["class"] == "bad_spec"
    assert result["source"] == "sidecar"


def test_sidecar_red_tests_failing_fires_halt(helper, fixtures_dir):
    """sidecar-red-tests-failing.json with matching storyId → halt via sidecar."""
    sidecar = fixtures_dir / "sidecar-red-tests-failing.json"
    result = helper.check_halt(
        session="ignored",
        story_id="4-3-quota-reset",
        sidecar_path=sidecar,
    )
    assert result["halt"] is True
    assert result["class"] == "red_tests_failing"
    assert result["source"] == "sidecar"
    assert len(result["files_affected"]) == 4


def test_sidecar_malformed_falls_through(helper, fixtures_dir, monkeypatch):
    """Malformed sidecar JSON is treated as absent — fall through to grep.

    With ``run_tmux`` stubbed to return an empty capture, the grep step
    finds nothing and the helper returns ``{"halt": false}``.
    """
    _stub_capture_pane_empty(helper, monkeypatch)
    sidecar = fixtures_dir / "negative-sidecar-malformed.json"
    result = helper.check_halt(
        session="ignored",
        story_id="any-story-id",
        sidecar_path=sidecar,
    )
    assert result["halt"] is False


def test_sidecar_story_id_mismatch_falls_through(helper, fixtures_dir, monkeypatch):
    """A valid sidecar whose storyId mismatches → fall through to grep.

    Protects against stale sidecars from a prior story being mistaken for
    a fresh HALT signal on the current one.
    """
    _stub_capture_pane_empty(helper, monkeypatch)
    sidecar = fixtures_dir / "sidecar-intent-gap.json"  # storyId = K-3-tiered-window
    result = helper.check_halt(
        session="ignored",
        story_id="some-other-story",
        sidecar_path=sidecar,
    )
    # Sidecar didn't match → grep ran (empty pane) → no halt.
    assert result["halt"] is False
    assert result.get("source") != "sidecar"
