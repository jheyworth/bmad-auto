"""T3 — Preflight HALT e2e test.

Variant: fixture is missing `_bmad-output/planning-artifacts/epics.md`,
which SKILL.md:146 declares as a HALT trigger ("epics.md not found").

This test is the cheapest e2e variant (<60s) and validates that the
driver harness works end-to-end: tmpdir prep, symlink setup, tmux
spawn, claude session, invocation paste, HALT detection. If T3 fails,
nothing else in the e2e suite can be trusted.
"""

from __future__ import annotations

import shutil
import sys

import pytest

# Tests are loaded via importlib — add the tests/ dir to sys.path so
# `import e2e_driver` works from inside the test files.
_HERE = __import__("pathlib").Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from e2e_driver import run_e2e  # noqa: E402
from e2e_assertions import t3_preflight_halt_assertions  # noqa: E402


@pytest.mark.e2e
@pytest.mark.e2e_fast
def test_preflight_halt_on_missing_epics(
    happy_fixture_source,
    preflight_halt_omit,
    e2e_tmpdir,
):
    """When epics.md is absent, /bmad-auto HALTs at Stage 0 step 6."""

    # Preflight requirements that must be present on the host machine.
    if shutil.which("tmux") is None:
        pytest.skip("tmux not on PATH; preflight HALT test requires tmux")
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not on PATH")

    result = run_e2e(
        fixture_source=happy_fixture_source,
        tmpdir=e2e_tmpdir,
        invocation="/bmad-auto --headless --epics 99",
        expected="preflight-halted",
        timeout_key="preflight-halt",
        omit_files=preflight_halt_omit,
    )

    failures = t3_preflight_halt_assertions(result)
    assert not failures, "\n".join(["T3 assertion failures:", *failures])
