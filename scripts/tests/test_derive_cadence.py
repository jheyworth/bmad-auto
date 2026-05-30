"""CLI tests for the ``derive-cadence`` subcommand.

Uses Option B (subprocess) — derive-cadence is a CLI-shaped function
whose contract is a bare integer printed to stdout. The tiered table
(1-3 → 45, 4-7 → 30, 8+ → 20) is exercised at each tier boundary plus
a clear "high-volume" sample, plus the error path (count=0 → exit 1).
"""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "story_count,expected_cadence",
    [
        (1, 45),   # bottom of low tier
        (3, 45),   # top of low tier
        (7, 30),   # top of mid tier
        (12, 20),  # well into high-volume tier
    ],
)
def test_derive_cadence_valid_counts(helper_script_path, story_count, expected_cadence):
    """Each tier maps to its documented cadence and exits 0."""
    result = subprocess.run(
        [
            sys.executable,
            str(helper_script_path),
            "derive-cadence",
            "--story-count",
            str(story_count),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"unexpected exit {result.returncode}; stderr={result.stderr!r}"
    )
    assert result.stdout.strip() == str(expected_cadence)


def test_derive_cadence_rejects_zero(helper_script_path):
    """story-count=0 → exit 1 with a stderr message (no stdout value)."""
    result = subprocess.run(
        [
            sys.executable,
            str(helper_script_path),
            "derive-cadence",
            "--story-count",
            "0",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout.strip() == ""
    assert "story-count" in result.stderr.lower()
