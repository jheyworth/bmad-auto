"""Shared pytest fixtures for the bmad-auto-helper test suite.

The helper lives at ``skills/bmad-auto/scripts/bmad-auto-helper.py``. Its
filename uses a hyphen, which is not a valid Python identifier, so plain
``import`` does not work. We load it via ``importlib.util.spec_from_file_location``
and expose it as a fixture so unit-test files can call library functions
(``check_halt``, ``derive-cadence`` math, ``read_sprint_status``, etc.) directly.

Fixtures provided:
    helper             — the loaded helper module.
    helper_script_path — absolute Path to the helper script (for subprocess).
    fixtures_dir       — Path to the skill-local ``test-fixtures/halt-detection/``.
    mock_tmux          — pytest fixture that patches ``helper.run_tmux`` and
                          returns a controllable mock callers can configure.
    sprint_status_tmp  — tmp_path-rooted ``_bmad-output/implementation-artifacts/``
                          directory plus a helper to write {story: status} maps.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import types
from typing import Callable
from unittest.mock import MagicMock

import pytest


# Path to the helper script (filename has a hyphen — not directly importable).
_HELPER_FILENAME = "bmad-auto-helper.py"
_HELPER_PATH = (pathlib.Path(__file__).resolve().parent.parent / _HELPER_FILENAME)

# Fixtures live inside the skill so the folder is self-sufficient. Resolve
# from the skill root (tests/ -> scripts/ -> bmad-auto/).
_SKILL_ROOT = pathlib.Path(__file__).resolve().parents[2]
_FIXTURES_BASE = _SKILL_ROOT / "test-fixtures"
_FIXTURES_DIR = _FIXTURES_BASE / "halt-detection"


def _load_helper_module() -> types.ModuleType:
    """Load the hyphen-named helper script as a Python module."""
    spec = importlib.util.spec_from_file_location(
        "bmad_auto_helper", str(_HELPER_PATH)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load helper module from {_HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    # Make the module importable by name so it survives multiple reloads
    # without polluting sys.modules with stale state.
    sys.modules["bmad_auto_helper"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def helper_script_path() -> pathlib.Path:
    """Absolute path to the helper script (for subprocess invocations)."""
    return _HELPER_PATH


@pytest.fixture
def helper() -> types.ModuleType:
    """Reload-isolated copy of the helper module.

    Each test gets a fresh module so monkey-patches on ``run_tmux`` /
    ``read_sprint_status`` / ``time.sleep`` from one test do not leak into
    the next. The reload is cheap (~1ms).
    """
    return _load_helper_module()


@pytest.fixture(scope="session")
def fixtures_dir() -> pathlib.Path:
    """Path to the halt-detection fixture directory.

    Skips the test (rather than erroring out) if the fixtures are absent —
    keeps the suite resilient when run from an unusual cwd.
    """
    if not _FIXTURES_DIR.is_dir():
        pytest.skip(f"halt-detection fixtures not found at {_FIXTURES_DIR}")
    return _FIXTURES_DIR


@pytest.fixture
def mock_tmux(helper, monkeypatch) -> MagicMock:
    """Patch ``helper.run_tmux`` with a MagicMock and return it.

    Default behavior: returns an empty successful CompletedProcess. Tests
    override ``.return_value`` or ``.side_effect`` to inject specific
    capture-pane bodies or non-zero exits.
    """
    mock = MagicMock(
        return_value=subprocess.CompletedProcess(
            args=["tmux"], returncode=0, stdout="", stderr=""
        )
    )
    monkeypatch.setattr(helper, "run_tmux", mock)
    return mock


@pytest.fixture
def fast_sleep(helper, monkeypatch) -> None:
    """Replace ``time.sleep`` inside the helper module with a no-op.

    Used by monitor tests to keep the suite fast (<5s). Note: the helper
    imports ``time`` and calls ``time.sleep(...)`` — we patch the attribute
    on the helper's already-imported ``time`` reference.
    """
    monkeypatch.setattr(helper.time, "sleep", lambda _seconds: None)


@pytest.fixture
def sprint_status_tmp(tmp_path) -> tuple[pathlib.Path, Callable[[dict[str, str]], None]]:
    """Provide a tmp ``_bmad-output/implementation-artifacts/`` dir + a writer.

    Returns ``(repo_root, write_fn)``.

    The writer accepts a ``{story_id: status}`` dict and renders a minimal
    valid sprint-status.yaml at the canonical location. The helper's
    ``read_sprint_status`` walks up from CWD looking for ``_bmad-output``,
    so callers typically pair this with ``monkeypatch.chdir(repo_root)``
    or with patching ``helper._find_repo_root``.
    """
    artifacts = tmp_path / "_bmad-output" / "implementation-artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    path = artifacts / "sprint-status.yaml"

    def write(stories: dict[str, str]) -> None:
        lines = ["development_status:"]
        for story_id, status in stories.items():
            lines.append(f"  {story_id}: {status}")
        path.write_text("\n".join(lines) + "\n")

    # Seed an empty (but parseable) file so reads before the first write
    # return {} instead of erroring out.
    write({})
    return tmp_path, write


# --- E2E fixtures ------------------------------------------------------------
#
# Fixtures used only by the e2e suite (test_e2e_*.py). Kept here because
# pytest auto-loads conftest.py and tests in this dir need them. Marked
# with the `e2e` marker so they're opt-in (`pytest -m e2e`).

import shutil  # noqa: E402

_E2E_FIXTURE_ROOT = _FIXTURES_BASE / "e2e"


@pytest.fixture(scope="session")
def e2e_fixture_root() -> pathlib.Path:
    """Path to the committed e2e fixture root. Skips if absent."""
    if not _E2E_FIXTURE_ROOT.is_dir():
        pytest.skip(f"e2e fixture root not found at {_E2E_FIXTURE_ROOT}")
    return _E2E_FIXTURE_ROOT


@pytest.fixture
def happy_fixture_source(e2e_fixture_root) -> pathlib.Path:
    """Source dir for the 'happy' variant (used by T1 + T4)."""
    src = e2e_fixture_root / "happy"
    if not src.is_dir():
        pytest.skip(f"happy fixture not found at {src}")
    return src


@pytest.fixture
def phase1_fail_overlay() -> dict[str, str]:
    """Overlay files for T2: plants a [CRITICAL] FAIL marker in brief.md.

    The unknowns-hunter subagent reads upstream artifacts looking for
    unresolved unknowns. A [CRITICAL] marker explicitly flagged as a
    blocker is the most reliable way to trigger a FAIL-severity finding
    from any reasonable LLM scanner. The orchestrator's headless-mode
    FAIL HALT (SKILL.md:457) is what we're actually testing.
    """
    return {
        "_bmad-output/planning-artifacts/briefs/e2e/brief.md": (
            "# Project Brief — bmad-auto e2e fixture (phase1-fail variant)\n"
            "\n"
            "## Problem\n"
            "\n"
            "Verify that `/bmad-auto` HALTs in Phase 1 when Headless mode\n"
            "encounters a FAIL-severity finding (per SKILL.md:457).\n"
            "\n"
            "## CRITICAL — unresolved blocking unknown\n"
            "\n"
            "[CRITICAL] This fixture declares a dependency on the package\n"
            "`madeup-pkg-2076`, which does not exist in any package registry.\n"
            "This is a deliberately planted FAIL-severity finding for the\n"
            "bmad-auto e2e test fixture. The Phase 1 unknowns-hunter MUST\n"
            "flag this as severity=FAIL because the package cannot be\n"
            "installed, breaking the entire epic before any story can run.\n"
            "\n"
            "This finding cannot be deferred — it blocks Phase 2 entry until\n"
            "resolved or explicitly waived. Headless mode must HALT here\n"
            "for operator triage.\n"
            "\n"
            "## Goals\n"
            "\n"
            "- Trigger Phase 1.e parallel-scan FAIL detection\n"
            "- Verify the headless FAIL HALT path\n"
        ),
    }


@pytest.fixture
def preflight_halt_omit() -> tuple[str, ...]:
    """Files to omit from the happy fixture to produce a preflight HALT.

    Removing epics.md triggers SKILL.md:146:
        "epics.md not found at _bmad-output/planning-artifacts/epics.md"
    """
    return ("_bmad-output/planning-artifacts/epics.md",)


@pytest.fixture
def e2e_tmpdir(tmp_path) -> pathlib.Path:
    """Fixture tmpdir for the prepared e2e fixture repo.

    pytest's tmp_path is preserved on test failure (under the pytest
    cache dir), so failed runs leave the materialized
    fixture available for postmortem inspection.
    """
    return tmp_path / "fixture-repo"
