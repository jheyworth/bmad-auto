"""T4 — Express consent gate e2e test.

Variant: happy fixture, Express mode (no `--headless`). The orchestrator
prints the Express signposting block and the `Proceed? [y/N]` prompt
(SKILL.md:204-215). The test responds `y`, then validates that the
full T1 assertion bundle passes — confirming both that the HITL gate
fires and that Express mode produces the same artifacts as Headless.

Runtime budget: 90 minutes — same as T1.
"""

from __future__ import annotations

import shutil
import sys

import pytest

_HERE = __import__("pathlib").Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from e2e_driver import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    prepare_fixture_repo,
    send_input,
    spawn_orchestrator,
    teardown,
    wait_for_pane_marker,
    wait_for_terminal_state,
)
from e2e_assertions import t4_express_consent_assertions  # noqa: E402


@pytest.mark.e2e
@pytest.mark.e2e_slow
def test_express_consent_gate_then_happy_path(
    happy_fixture_source,
    e2e_tmpdir,
):
    """Express mode prompts for consent, then completes the epic on `y`."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux not on PATH")
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not on PATH")

    fixture_root = prepare_fixture_repo(
        happy_fixture_source, e2e_tmpdir,
    )

    # Express invocation — no --headless flag
    session = spawn_orchestrator(
        fixture_root,
        invocation="/bmad-auto --epics 99",
    )

    try:
        # Wait for the consent prompt to render. The Express signposting
        # block ends with "Proceed? `[y/N]`" per SKILL.md:215.
        consent_shown = wait_for_pane_marker(
            session, marker="Proceed?", timeout_seconds=180,
        )
        if not consent_shown:
            pytest.fail(
                "Express consent prompt did not render within 180s. "
                "Signposting may have changed or claude session is stuck."
            )

        # Respond `y` to advance the run.
        send_input(session, "y")

        # Now wait for the full happy-path completion (digest-rendered).
        result = wait_for_terminal_state(
            session, fixture_root,
            expected="digest-rendered",
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS["happy-express"],
        )

    finally:
        teardown(session)

    failures = t4_express_consent_assertions(result)
    assert not failures, "\n".join(["T4 assertion failures:", *failures])
