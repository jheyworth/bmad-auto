"""Monitor happy path: sprint-status flips to ``done`` → final_state=completed.

Patches:
  - ``time.sleep`` → no-op (keeps the suite fast).
  - ``run_tmux`` → empty successful capture-pane (no HALT triggers, never
    fingerprints into a stall before the sprint-status flip wins).
  - ``read_sprint_status`` → returns the story as ``done`` on the first poll.
  - ``_find_repo_root`` → returns a tmp_path so context-file writes don't
    leak into the real ``_bmad-output/`` tree.

Asserts:
  - ``cmd_monitor`` returns EXIT_OK.
  - The emitted JSON has ``final_state == "completed"`` and
    ``exit_reason == "sprint_status_done"``.
"""

from __future__ import annotations

import argparse
import json
import subprocess


def _build_args(session="auto-K-1-r1", story_id="K-1-foo", **overrides) -> argparse.Namespace:
    base = dict(
        session=session,
        story_id=story_id,
        run_id="r1",
        cadence_seconds=0,
        stall_warmup_polls=7,
        stall_trip_polls=3,
        timeout_minutes=60,
        sidecar_path=None,
        verbose=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_monitor_completes_when_sprint_status_done(
    helper, fast_sleep, tmp_path, monkeypatch, capsys
):
    # Empty capture-pane (no HALT triggers, deterministic SHA1).
    def fake_run_tmux(args):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)

    # First call returns "done" so the sprint-status branch wins immediately.
    monkeypatch.setattr(
        helper, "read_sprint_status", lambda repo_root: {"K-1-foo": "done"}
    )

    # Ensure context-file writes (if any) land in the sandbox.
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    args = _build_args()
    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "completed"
    assert payload["exit_reason"] == "sprint_status_done"
    assert payload["session_name"] == "auto-K-1-r1"
    assert payload["polls"] >= 1
