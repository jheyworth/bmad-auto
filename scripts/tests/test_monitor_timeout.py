"""Monitor TIMEOUT path: no terminal signal + elapsed > timeout → final_state=timeout.

With ``--timeout-minutes 0`` the timeout trips as soon as ``int(time.time()
- start)`` exceeds zero. To make the test deterministic (and unaffected
by real wall-clock jitter), we patch ``time.time`` to return an advancing
counter so elapsed grows by 1 second per poll.

To prevent the stall path from firing first, each poll's capture-pane
content is unique (different SHA1 fingerprints) — so the deque never
has all-identical entries.
"""

from __future__ import annotations

import argparse
import itertools
import json
import subprocess


def _build_args() -> argparse.Namespace:
    return argparse.Namespace(
        session="auto-K-timeout-r1",
        story_id="K-timeout",
        run_id="r1",
        cadence_seconds=0,
        stall_warmup_polls=99,  # never trip stall in this test
        stall_trip_polls=99,
        timeout_minutes=0,
        sidecar_path=None,
        verbose=False,
    )


def test_monitor_times_out(helper, fast_sleep, tmp_path, monkeypatch, capsys):
    poll_counter = itertools.count()

    # Each capture-pane response is unique → fingerprints never match →
    # stall path remains dormant.
    def fake_run_tmux(args):
        idx = next(poll_counter)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=f"poll-{idx}\n", stderr=""
        )

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)
    monkeypatch.setattr(helper, "read_sprint_status", lambda repo_root: {})
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    # Advance the clock by 1 second per call. The helper's `start` snapshot
    # uses the first call (returning 1000.0); subsequent calls inside the
    # loop return 1001, 1002, ... so elapsed grows monotonically.
    time_counter = itertools.count(1000)

    def fake_time():
        return float(next(time_counter))

    monkeypatch.setattr(helper.time, "time", fake_time)

    args = _build_args()
    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "timeout"
    assert payload["exit_reason"] == "exceeded_0m"
    assert payload["session_name"] == "auto-K-timeout-r1"
