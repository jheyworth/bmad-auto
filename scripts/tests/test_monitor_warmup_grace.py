"""Monitor warmup-grace: pasted /goal directive prose at poll #1 does NOT
classify halt when ``--grep-warmup-polls`` is engaged. After the warmup
window expires, sprint-status flips to ``done`` and the monitor exits
``completed`` cleanly.

Regression for the 2026-05-27 v5 smoke-run false-positive
(runId 20260527T044517Z). Without the warmup grace, the monitor's poll #1
grep fallback false-positives on directive 8's bare ``loopback overflow``
substring inside the pasted /goal directive enumeration. Provenance:
``bmad-auto-v5-smoke-fix-1.md``.
"""

from __future__ import annotations

import argparse
import json
import subprocess


def _build_args(**overrides) -> argparse.Namespace:
    base = dict(
        session="auto-K-100-2-r1",
        story_id="100-2",
        run_id="r1",
        cadence_seconds=0,
        stall_warmup_polls=7,
        stall_trip_polls=3,
        timeout_minutes=60,
        sidecar_path=None,
        grep_warmup_polls=2,
        verbose=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_monitor_warmup_grace_suppresses_grep_on_pasted_directive(
    helper, fast_sleep, tmp_path, fixtures_dir, monkeypatch, capsys
):
    """Poll #1 + #2: capture-pane is dominated by the pasted /goal
    directive prose; without warmup grace, grep false-positives on
    ``loopback overflow``. With warmup grace (default 2 polls), grep is
    suppressed during the window. Poll #3: sprint-status flips to
    ``done`` and the monitor returns ``completed``.
    """
    dangerous = (fixtures_dir / "halt-context-100-2-directive-prose.txt").read_text()

    def fake_run_tmux(args):
        # kill-session has no stdout body to mock.
        if args and args[0] == "kill-session":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=dangerous, stderr=""
        )

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)

    # Sprint-status returns {} for the first two polls (in warmup), then
    # flips to "done" on poll #3 (post-warmup).
    poll_counter = {"n": 0}

    def fake_sprint_status(_repo_root):
        poll_counter["n"] += 1
        if poll_counter["n"] >= 3:
            return {"100-2": "done"}
        return {}

    monkeypatch.setattr(helper, "read_sprint_status", fake_sprint_status)
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    args = _build_args()
    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "completed", (
        "warmup grace should suppress poll #1/#2 grep on dangerous fixture, "
        f"letting sprint-status flip win at poll #3; got {payload!r}"
    )
    assert payload["exit_reason"] == "sprint_status_done"
    assert payload["polls"] == 3


def test_monitor_without_warmup_grace_classifies_halt_at_poll_1(
    helper, fast_sleep, tmp_path, fixtures_dir, monkeypatch, capsys
):
    """Pinning the bug for the disabled-warmup case. With
    ``grep_warmup_polls=0`` the monitor's poll #1 grep fires on the
    dangerous fixture and classifies ``halted`` immediately — matching
    the 2026-05-27 v5 smoke-run failure mode.

    This is the regression baseline: when an operator deliberately
    disables the warmup grace (``--grep-warmup-polls 0``), they reproduce
    the historical false-positive. The test pins this behavior so a
    future structural-guard upgrade (approach (c), explicitly deferred)
    has a diff baseline.
    """
    dangerous = (fixtures_dir / "halt-context-100-2-directive-prose.txt").read_text()

    def fake_run_tmux(args):
        if args and args[0] == "kill-session":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=dangerous, stderr=""
        )

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)
    monkeypatch.setattr(helper, "read_sprint_status", lambda _r: {})
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    args = _build_args(grep_warmup_polls=0)
    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "halted"
    assert payload["halt_class"] == "loopback_overflow"
    assert payload["halt_source"] == "grep"
    assert payload["polls"] == 1  # halt fires immediately at poll #1
