"""Monitor HALT path: sidecar present at poll-start → final_state=halted.

Drops a valid sidecar fixture at the path monitor expects, patches
``run_tmux`` to return an innocuous capture (no HALT triggers in the
grep path), and asserts the sidecar-primary check fires.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess


def _build_args(session, story_id, sidecar_path) -> argparse.Namespace:
    return argparse.Namespace(
        session=session,
        story_id=story_id,
        run_id="r1",
        cadence_seconds=0,
        stall_warmup_polls=7,
        stall_trip_polls=3,
        timeout_minutes=60,
        sidecar_path=str(sidecar_path),
        verbose=False,
    )


def test_monitor_halts_via_sidecar(
    helper, fast_sleep, tmp_path, fixtures_dir, monkeypatch, capsys
):
    # Stage a real fixture as the sidecar at a tmp path.
    sidecar_src = fixtures_dir / "sidecar-intent-gap.json"
    sidecar_path = tmp_path / "quick-dev-halt-K-3-tiered-window.json"
    shutil.copy(sidecar_src, sidecar_path)

    # Innocuous capture-pane content — grep path returns no halt.
    def fake_run_tmux(args):
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="some progress output\n", stderr=""
        )

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)
    # Sprint-status never flips.
    monkeypatch.setattr(helper, "read_sprint_status", lambda repo_root: {})
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    args = _build_args(
        session="auto-K-K-3-tiered-window-r1",
        story_id="K-3-tiered-window",
        sidecar_path=sidecar_path,
    )

    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "halted"
    assert payload["halt_class"] == "intent_gap"
    assert payload["halt_source"] == "sidecar"
    assert "context_file" in payload
    # Context file should land under the sandbox repo root.
    assert str(tmp_path) in payload["context_file"]
