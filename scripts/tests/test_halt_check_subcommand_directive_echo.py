"""Smoke-fix-3 T7 follow-up: cmd_halt_check subcommand applies
directive-echo suppression when --run-id is provided.

Bug background: smoke-fix-2 G2 added ``goal_file_path`` to ``check_halt``
(the function) and to ``cmd_monitor`` (the subcommand), but
``cmd_halt_check`` (the peer subcommand) was left without the new param
threading. T2 added ``directives_file_path`` to ``check_halt`` +
``cmd_monitor``; the asymmetry on ``cmd_halt_check`` widened to TWO
unsupported suppression paths.

Result of the asymmetry: operators / scripts invoking the
``halt-check`` subcommand directly against a session that just pasted
``/goal`` directives would see false-positive HALTs that the monitor
would never report on the same session.

This T7 follow-up wires ``cmd_halt_check`` to read the spawn-state
sidecar by ``session_id + run_id`` (same pattern as ``cmd_monitor``)
and thread both paths through to ``check_halt``. Optional ``--run-id``
keeps pre-fix callers back-compat.

Two tests:
  - Test 1 (subcommand baseline) — no ``--run-id`` → no spawn-sidecar
    context → suppression is a no-op → the smoke-run-2 pane still
    fires the documented false-positive. Matches ``cmd_monitor``'s
    behavior when its own sidecar is absent.
  - Test 2 (subcommand fix) — ``--run-id`` provided + valid
    spawn-sidecar on disk → suppression fires → ``halt=False``.
"""

from __future__ import annotations

import argparse
import json
import subprocess


def _stub_capture(helper, monkeypatch, text: str, returncode: int = 0, stderr: str = ""):
    """Make ``helper.run_tmux`` return a CompletedProcess with given stdout."""

    def fake(args):
        return subprocess.CompletedProcess(
            args=args, returncode=returncode, stdout=text, stderr=stderr
        )

    monkeypatch.setattr(helper, "run_tmux", fake)


def _make_args(**overrides) -> argparse.Namespace:
    """Build a Namespace with cmd_halt_check's expected fields.

    Mirrors the argparse defaults set in build_parser()'s halt-check block.
    """
    defaults = {
        "session": "sess",
        "story_id": "100-2",
        "sidecar_path": None,
        "tail_lines": 60,
        "run_id": None,
        "no_directive_echo_suppression": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_halt_check_subcommand_without_run_id_documents_existing_bug(
    helper, fixtures_dir, monkeypatch, capsys
):
    """Baseline (regression pin): ``cmd_halt_check`` without ``--run-id``
    has no spawn-sidecar context, so directive-echo suppression is a
    no-op. The verbatim smoke-run-2 pane fires the documented false-
    positive (``red_tests_failing`` from grep matching directive #8 prose).

    This pin protects against an accidental future change that wires up
    suppression-by-default in ``cmd_halt_check`` AND silently breaks the
    structural guards in ``check_halt``. Without this baseline the
    guard-loss would go silent.
    """
    fixture = fixtures_dir / "halt-context-100-2-directive-echo-poll3.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())
    args = _make_args()
    rc = helper.cmd_halt_check(args)
    assert rc == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out.strip())
    assert result["halt"] is True, (
        "subcommand without --run-id should produce the pre-fix false-positive; "
        f"got {result!r}"
    )
    assert result["class"] == "red_tests_failing"
    assert result["source"] == "grep"


def test_halt_check_subcommand_with_run_id_applies_suppression(
    helper, fixtures_dir, monkeypatch, tmp_path, capsys
):
    """Fix contract: ``cmd_halt_check`` with ``--run-id`` reads the
    spawn-state sidecar, threads ``goal_file_path`` through ``check_halt``,
    and suppresses the directive-echo false-positive.

    Mirrors ``cmd_monitor``'s suppression behavior: when the spawn-state
    sidecar exists and contains the goal-file path, the same pane content
    that would otherwise false-positive returns ``halt=False``.
    """
    # Place a spawn-state sidecar at the canonical location under tmp_path.
    run_state = tmp_path / "_bmad-output" / ".run-state"
    run_state.mkdir(parents=True, exist_ok=True)
    spawn_sidecar = run_state / "spawn-100-2-test_run_id.json"
    goal_file = fixtures_dir / "goal-100-2.txt"
    spawn_sidecar.write_text(
        json.dumps(
            {
                "session_name": "sess",
                "spawned_at": "2026-05-27T07:43:11Z",
                "goal_file_path": str(goal_file),
            }
        )
    )

    # Repoint the helper's repo-root resolver to our tmp_path so the
    # spawn-sidecar read targets the file we just wrote.
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    fixture = fixtures_dir / "halt-context-100-2-directive-echo-poll3.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())

    args = _make_args(run_id="test_run_id")
    rc = helper.cmd_halt_check(args)
    assert rc == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out.strip())
    assert result["halt"] is False, (
        "directive-echo suppression should fire when --run-id provides "
        f"spawn-sidecar context; got {result!r}"
    )


def test_halt_check_subcommand_no_suppression_flag_disables_even_with_run_id(
    helper, fixtures_dir, monkeypatch, tmp_path, capsys
):
    """``--no-directive-echo-suppression`` opt-out: even with a valid
    spawn-sidecar reachable via ``--run-id``, the flag forces the
    pre-fix behavior. Mirrors ``cmd_monitor``'s flag of the same name.

    Important for debugging: an operator chasing a real HALT that
    coincidentally overlaps directive prose can disable suppression
    to see the raw grep result.
    """
    # Same setup as the fix-contract test: spawn-sidecar exists and is valid.
    run_state = tmp_path / "_bmad-output" / ".run-state"
    run_state.mkdir(parents=True, exist_ok=True)
    spawn_sidecar = run_state / "spawn-100-2-test_run_id.json"
    goal_file = fixtures_dir / "goal-100-2.txt"
    spawn_sidecar.write_text(
        json.dumps(
            {
                "session_name": "sess",
                "spawned_at": "2026-05-27T07:43:11Z",
                "goal_file_path": str(goal_file),
            }
        )
    )

    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    fixture = fixtures_dir / "halt-context-100-2-directive-echo-poll3.txt"
    _stub_capture(helper, monkeypatch, fixture.read_text())

    args = _make_args(run_id="test_run_id", no_directive_echo_suppression=True)
    rc = helper.cmd_halt_check(args)
    assert rc == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out.strip())
    assert result["halt"] is True, (
        "--no-directive-echo-suppression should restore the pre-fix "
        f"false-positive even with a valid spawn-sidecar; got {result!r}"
    )
    assert result["class"] == "red_tests_failing"
