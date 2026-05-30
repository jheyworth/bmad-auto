"""Bug 2 reproducer: monitor misses sprint-status flip when ``--story-id``
is the short form (e.g. ``100-2``) and the sprint-status.yaml key is
the full slug emitted by ``bmad-sprint-planning`` (e.g.
``100-2-validation-sandbox-paths-cmd``).

Provenance: smoke-run-3 (runId ``20260527T073029Z``) of
epic-100. Post-Workaround-A-nudge, the spawned agent landed the work
cleanly (12m37s cook), flipped sprint-status through the full lifecycle
(``ready-for-dev → in-progress → review → done``), and went idle at the
``Goal achieved`` prompt. The helper monitor polled 17 times over 765s
before declaring ``stalled`` on the fingerprint window. The work LANDED
correctly; the orchestrator-side detection was wrong.

Root cause (see [`bmad-auto-v5-smoke-fix-3.md`](bmad-auto-v5-smoke-fix-3.md) T4):
``_story_status`` does exact (case-insensitive) key matching only. The
orchestrator passes ``--story-id 100-2`` (short form — matches session
name ``auto-K-100-2-<runId>`` and sidecar filenames), but the sprint-
status producer writes the full slug ``100-2-validation-sandbox-paths-cmd``.
``_story_status`` returns ``None`` on every poll, the completion branch
never wins, the idle pane's identical fingerprints accumulate, stall trips.

This file pins both:
  - the unit-level invariant (``_story_status`` resolves short → full-slug)
  - the end-to-end behavior (``cmd_monitor`` returns ``completed``, not
    ``stalled``, when sprint-status uses full-slug keys)

The pre-fix helper fails the unit invariant and the end-to-end test.
The post-fix helper passes both.
"""

from __future__ import annotations

import argparse
import json
import subprocess


# Realistic values from smoke-run-3 (runId 20260527T073029Z).
SHORT_STORY_ID = "100-2"
FULL_SLUG_KEY = "100-2-validation-sandbox-paths-cmd"


def _build_args(**overrides) -> argparse.Namespace:
    base = dict(
        session=f"auto-K-{SHORT_STORY_ID}-r1",
        story_id=SHORT_STORY_ID,
        run_id="r1",
        cadence_seconds=0,
        stall_warmup_polls=1,
        stall_trip_polls=2,
        timeout_minutes=60,
        sidecar_path=None,
        grep_warmup_polls=2,
        no_directive_echo_suppression=True,
        verbose=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


# --- Unit-level: _story_status resolves short storyId → full-slug key --------


def test_story_status_resolves_short_id_against_full_slug_key(helper):
    """The orchestrator's storyId convention is short (``100-2``); the
    sprint-status producer writes the full slug. The matcher must bridge
    the two.
    """
    sprint_status = {FULL_SLUG_KEY: "done"}
    assert helper._story_status(sprint_status, SHORT_STORY_ID) == "done"


def test_story_status_still_matches_exact_keys(helper):
    """Don't regress the existing tests' convention — exact-match callers
    (e.g. ``story_id="K-1-foo"`` against ``{"K-1-foo": ...}``) keep working.
    """
    sprint_status = {"K-1-foo": "done", "K-2-bar": "in-progress"}
    assert helper._story_status(sprint_status, "K-1-foo") == "done"
    assert helper._story_status(sprint_status, "K-2-bar") == "in-progress"


def test_story_status_case_insensitive_exact_match(helper):
    """Preserve the existing case-insensitive exact-match behavior."""
    sprint_status = {"100-2-Validation-Sandbox-Paths-CMD": "done"}
    assert helper._story_status(sprint_status, "100-2-validation-sandbox-paths-cmd") == "done"


def test_story_status_returns_none_when_prefix_is_ambiguous(helper):
    """Defensive: if two keys would prefix-match the short storyId,
    refuse to guess. Returning None keeps the monitor polling rather than
    racing to the wrong story's status. (This shape doesn't occur in
    practice — one storyId per session — but the matcher should fail safe.)
    """
    sprint_status = {
        "100-2-validation-sandbox-paths-cmd": "done",
        "100-2-some-other-collision": "in-progress",
    }
    assert helper._story_status(sprint_status, "100-2") is None


def test_story_status_returns_none_when_no_key_matches(helper):
    """Unknown storyId → None (callers keep polling)."""
    sprint_status = {"100-1-validation-sandbox-where-cmd": "done"}
    assert helper._story_status(sprint_status, "100-2") is None


def test_story_status_requires_prefix_not_substring(helper):
    """Segment-boundary discipline: the match is ``key.startswith(story_id + "-")``,
    NOT substring containment. A story_id that appears *inside* a key
    (but not at the start) must not match — otherwise routine-storyId
    fragments would race against unrelated stories.
    """
    sprint_status = {"100-2-validation-sandbox-paths-cmd": "done"}
    # ``2-validation`` is a substring of the key but NOT a prefix.
    assert helper._story_status(sprint_status, "2-validation") is None
    # ``validation-sandbox`` likewise — substring inside the slug.
    assert helper._story_status(sprint_status, "validation-sandbox") is None


def test_story_status_bare_epic_number_returns_none_via_ambiguity_guard(helper):
    """Realistic sprint-status has multiple stories per epic (plus the
    ``<epic>-retrospective`` housekeeping key). If a caller passed a bare
    epic number (``100``), the prefix ``100-`` would match three keys at
    once, and the ambiguity guard would correctly return ``None``.

    Pins the practical safety: the orchestrator only passes story-shaped
    ``--story-id`` values to ``monitor``, and even if a bare epic number
    leaked through, the ambiguity guard would catch it for any real
    sprint-status.yaml (which always has >1 story per epic in this codebase).
    """
    sprint_status = {
        "100-1-validation-sandbox-where-cmd": "done",
        "100-2-validation-sandbox-paths-cmd": "done",
        "100-retrospective": "done",
    }
    # Bare epic number → 3 prefix matches → ambiguity guard → None.
    assert helper._story_status(sprint_status, "100") is None
    # But each story-shaped storyId still resolves unambiguously.
    assert helper._story_status(sprint_status, "100-1") == "done"
    assert helper._story_status(sprint_status, "100-2") == "done"


# --- End-to-end: cmd_monitor returns completed on the smoke-run-3 shape ------


def test_monitor_completes_when_sprint_status_uses_full_slug_key_for_short_story_id(
    helper, fast_sleep, tmp_path, monkeypatch, capsys
):
    """Reproduces smoke-run-3 Bug 2 end-to-end.

    Setup mirrors the production shape:
      - ``--story-id 100-2`` (short form, matching session name convention)
      - sprint-status.yaml key is ``100-2-validation-sandbox-paths-cmd: done``
      - capture-pane is the idle ``Goal achieved`` shape — identical SHA1
        every poll, so the stall window WOULD trip if the completion
        branch misses.

    Stall params are aggressive (warmup=1, trip=2) so this test takes ≤2
    polls. Without the fix, the completion branch returns None each poll,
    fingerprints accumulate identical, and the test sees
    ``final_state=stalled``. With the fix, poll #1's sprint-status read
    matches the full-slug key, the completion branch wins, and the test
    sees ``final_state=completed`` with ``exit_reason=sprint_status_done``.
    """
    # Idle-prompt capture-pane: identical every poll → identical fingerprints.
    def fake_run_tmux(args):
        if args and args[0] == "kill-session":
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="", stderr=""
            )
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="> Goal achieved\n│ Try a new prompt\n",
            stderr="",
        )

    monkeypatch.setattr(helper, "run_tmux", fake_run_tmux)

    # The production-shape sprint-status: full-slug key, no short-id key.
    # Story is already done by the time the monitor starts polling (mirrors
    # smoke-run-3: agent finished the work and went idle before the
    # monitor's stall window expired).
    monkeypatch.setattr(
        helper,
        "read_sprint_status",
        lambda _repo_root: {FULL_SLUG_KEY: "done"},
    )
    monkeypatch.setattr(helper, "_find_repo_root", lambda: tmp_path)

    args = _build_args()
    rc = helper.cmd_monitor(args)
    out = capsys.readouterr().out.strip()

    assert rc == helper.EXIT_OK
    payload = json.loads(out)
    assert payload["final_state"] == "completed", (
        "monitor should resolve short --story-id against the sprint-status "
        f"producer's full-slug key; got {payload!r}. This is smoke-run-3 "
        "Bug 2 — see bmad-auto-v5-smoke-fix-3.md T4."
    )
    assert payload["exit_reason"] == "sprint_status_done"
    assert payload["session_name"] == args.session
    assert payload["polls"] == 1
