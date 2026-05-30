"""Monitor STALL path: identical capture-pane across N polls → final_state=stalled.

The stall trip fires when ALL of:
  - len(fingerprints) == stall_trip_polls
  - poll >= stall_warmup_polls
  - all fingerprints in the deque are identical

This test uses ``--stall-warmup-polls 1 --stall-trip-polls 2`` so the
trip fires on the 2nd poll without us having to crank the loop count.
"""

from __future__ import annotations

import argparse
import json
import subprocess


def _build_args() -> argparse.Namespace:
    return argparse.Namespace(
        session="auto-K-stall-r1",
        story_id="K-stall",
        run_id="r1",
        cadence_seconds=0,
        stall_warmup_polls=1,
        stall_trip_polls=2,
        timeout_minutes=60,
        sidecar_path=None,
        verbose=False,
    )


def test_monitor_stalls_on_identical_fingerprints(
    helper, fast_sleep, tmp_path, monkeypatch, capsys
):
    # Identical capture-pane every poll → identical SHA1 → stall trip.
    def fake_run_tmux(args):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="idle prompt cursor\n", stderr=""
        )

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)
    monkeypatch.setattr(helper, "read_sprint_status", lambda repo_root: {})
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    args = _build_args()
    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "stalled"
    assert payload["exit_reason"] == "no_movement_2_polls"
    assert "context_file" in payload
    assert payload["polls"] >= 2
