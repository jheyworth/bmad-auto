"""Integration smoke test for ``kill`` against a real tmux session.

The ``spawn`` half of this smoke test would normally cover spawn + kill,
but ``cmd_spawn`` launches ``claude --dangerously-skip-permissions``
which is not present in typical test environments. Patching the spawn
command to use ``sleep 60`` instead would require helper changes that
are out of scope for the test suite, so we cover only the ``kill``
integration path here.

Approach:
  1. Manually create a tmux session via ``tmux new-session -d sleep 60``.
  2. Invoke the helper's ``kill`` subcommand.
  3. Assert the helper exits 0.
  4. Assert ``tmux has-session`` confirms the session is gone.

Skipped automatically when ``tmux`` is not on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import uuid

import pytest


pytestmark = pytest.mark.skipif(
    shutil.which("tmux") is None, reason="tmux not installed on PATH"
)


def test_kill_session_against_real_tmux(helper_script_path):
    """End-to-end: real tmux session → helper kill → session is gone."""
    session = f"smoke-test-bmad-auto-helper-{uuid.uuid4().hex[:8]}"

    # Create a long-running sleep session — survives until killed.
    create = subprocess.run(
        ["tmux", "new-session", "-d", "-s", session, "sleep", "60"],
        capture_output=True,
        text=True,
    )
    assert create.returncode == 0, (
        f"failed to create tmux session: stderr={create.stderr!r}"
    )

    try:
        # Sanity: tmux confirms the session exists before we kill it.
        before = subprocess.run(
            ["tmux", "has-session", "-t", session], capture_output=True, text=True
        )
        assert before.returncode == 0, "session should exist before kill"

        # Call helper kill.
        result = subprocess.run(
            [sys.executable, str(helper_script_path), "kill", "--session", session],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"helper kill failed: stderr={result.stderr!r}"
        )

        # Verify session is gone.
        after = subprocess.run(
            ["tmux", "has-session", "-t", session], capture_output=True, text=True
        )
        assert after.returncode != 0, "session should be gone after kill"

    finally:
        # Belt-and-braces cleanup if anything went sideways.
        subprocess.run(
            ["tmux", "kill-session", "-t", session],
            capture_output=True,
            text=True,
        )


def test_kill_idempotent_on_missing_session(helper_script_path):
    """Killing a nonexistent session must exit 0 (kill-on-already-dead is fine)."""
    nonexistent = f"smoke-test-bmad-auto-helper-nope-{uuid.uuid4().hex[:8]}"
    result = subprocess.run(
        [
            sys.executable,
            str(helper_script_path),
            "kill",
            "--session",
            nonexistent,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"kill on missing session should be idempotent; stderr={result.stderr!r}"
    )
