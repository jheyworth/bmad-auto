"""T1 — Happy-path headless e2e test (the headline e2e).

Variant: happy fixture, `--headless --epics 99` invocation. Drives all
four phases end-to-end. Tracer (story 99-1) joins the per-story fanout
loop in headless mode (Phase 2 collapses, SKILL.md:194), so both stories
run autonomously in tmux child sessions.

Runtime budget: 90 minutes. This is a slow test — marked `e2e_slow` so
it runs nightly only, not on every push.

Assertion bundle covers:
- Phase 1 findings schema + headless deferred invariant
- Story outputs (e2e-tracer.txt, e2e-fanout.txt) with expected content
- sprint-status monotonicity + final state = done
- Per-story end SHAs recorded
- Phase 4.a/b/c/d/e all produced their canonical sidecars
- Digest references the major artifacts
- No orphan HALT sidecars
"""

from __future__ import annotations

import shutil
import sys

import pytest

_HERE = __import__("pathlib").Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from e2e_driver import run_e2e  # noqa: E402
from e2e_assertions import t1_happy_headless_assertions  # noqa: E402


@pytest.mark.e2e
@pytest.mark.e2e_slow
def test_happy_path_headless(happy_fixture_source, e2e_tmpdir):
    """Full epic 99 completes cleanly in headless mode."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux not on PATH")
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not on PATH")

    result = run_e2e(
        fixture_source=happy_fixture_source,
        tmpdir=e2e_tmpdir,
        invocation="/bmad-auto --headless --epics 99",
        expected="digest-rendered",
        timeout_key="happy-headless",
    )

    failures = t1_happy_headless_assertions(result)
    assert not failures, "\n".join(["T1 assertion failures:", *failures])
