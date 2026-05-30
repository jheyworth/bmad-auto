"""T2 — Phase 1 FAIL HALT e2e test.

Variant: happy fixture with a planted `[CRITICAL]` FAIL marker in
brief.md (via the `phase1_fail_overlay` fixture). The Phase 1.e
parallel scan should detect a FAIL-severity finding, and headless
mode must HALT rather than silently proceed (SKILL.md:457).

Runtime budget: 10 minutes — should HALT well before reaching Phase 3.
"""

from __future__ import annotations

import shutil
import sys

import pytest

_HERE = __import__("pathlib").Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from e2e_driver import run_e2e  # noqa: E402
from e2e_assertions import t2_phase1_fail_halt_assertions  # noqa: E402


@pytest.mark.e2e
@pytest.mark.e2e_fast
def test_headless_halts_on_phase1_fail(
    happy_fixture_source,
    phase1_fail_overlay,
    e2e_tmpdir,
):
    """Headless mode HALTs at Stage 1.e when a FAIL finding is present."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux not on PATH")
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not on PATH")

    result = run_e2e(
        fixture_source=happy_fixture_source,
        tmpdir=e2e_tmpdir,
        invocation="/bmad-auto --headless --epics 99",
        expected="phase1-halted",
        timeout_key="phase1-halt",
        overlay_files=phase1_fail_overlay,
    )

    failures = t2_phase1_fail_halt_assertions(result)
    assert not failures, "\n".join(["T2 assertion failures:", *failures])
