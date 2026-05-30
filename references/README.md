# `/bmad-auto` — operator notes

This is a human-readable orientation file. It's not loaded by the LLM
during skill execution — it lives in `references/` because that's where
supplementary docs go in an Anthropic Skill, but `SKILL.md` doesn't
reference it, so the agent never reads it. Just for you.

For everything authoritative — what the skill does, how it runs, what
the gates mean — read [`SKILL.md`](../SKILL.md). This file is the
five-minute orientation you read before that, not instead of it.

## What this is

`/bmad-auto` is a per-epic execution conductor. You give it an epic that
has been hardened through the upstream BMAD pipeline (brief → spec → UX
→ architecture → epics → sprint-status), and it runs the epic end-to-end:
per-epic hardening, tracer-bullet via `/bmad-quick-dev`, autonomous
dev-fanout for the rest of the stories, quality gates, digest, and
retrospective.

The skill was designed against Alex Verhovsky's per-epic execution
pattern from the BMAD Discord (May 2026): heavy human-in-the-loop at
the beginning and end of an epic, autonomous in the middle. The tracer
bullet on story K-1 is where the architectural unknowns get resolved
for the rest of the epic.

## Quick start

You almost always want Express mode, which is the default:

    /bmad-auto --epics <K>

The skill walks Phase 1 (per-epic hybrid hardening) with you in the
session, then Phase 2 (tracer-bullet via `/bmad-quick-dev`, interactive),
then Phase 3 (autonomous dev-fanout in spawned tmux sessions, one per
story), then Phase 4 (quality gates + digest + retrospective + optional
correct-course).

### Phase 1 hardening at a glance

Stage 1.e runs two adversarial scans in parallel as Task subagents: an
unknowns-hunter (SPIKES method — Scope/Packages/Integrations/Knowledge/
Environment/Surface) and an edge-case-hunter (wraps `bmad-review-edge-case-hunter`
across the story list). The orchestrator collates findings into a single
triage table; you decide each row's disposition (resolve-now / defer-to-
digest / split-off) and may escalate any finding to `/good-ideas` mode
for deeper adversarial attack before deciding. The contract — schema,
severity calibration, headless-mode behavior, Phase 2 gate — lives in
[`SKILL.md`](../SKILL.md) Stage 1.e.

Other modes:

- `--headless` — best-effort autonomous. Phase 2 collapses into the
  Phase 3 fanout loop (the tracer becomes story 1). Operator only
  surfaces if quick-dev raises `intent_gap` or a quality gate fails.
- `--prep` / `--verify` / `--dev` — guided modal, the legacy v3
  pattern preserved. Each runs one phase and exits.

## Prerequisites

Stage 0 preflight verifies these and HALTs cleanly if missing:

- **`tmux`** — required for Phase 3 per-story session fanout. macOS:
  `brew install tmux`.
- **Python 3.11+** — required by the helper at
  `scripts/bmad-auto-helper.py` (Phase 3 spawn / monitor / cadence
  derivation). Stdlib-only, no external deps. macOS Sonoma+ ships
  3.11+ by default; verify with `python3 --version`.
- **BMad TEA module** — required for Stage 2.a (`bmad-testarch-atdd`),
  Stage 4.a (`bmad-testarch-trace`), Stage 4.b (`bmad-testarch-nfr`).
  Install via `/update-bmad` or directly:
  `npx bmad-method@next install --modules tea --tools claude-code`.
  Presence-only check; any installed TEA version is accepted.
- **`codex`** (optional, soft) — Phase 4.c adversarial review is
  skipped if not installed. macOS: `brew install codex-cli`.

`--prep` mode is the only exception: tmux + Python + TEA are not
required because Phase 1 doesn't invoke any of them.

## When NOT to use it

- Upstream pipeline isn't finished. If brief / PRD-or-SPEC / UX /
  architecture / epics.md don't exist, Phase 1.a will detect and
  surface this. The skill can auto-invoke missing autonomous upstream
  (e.g. `bmad-sprint-planning`) but it won't bootstrap from raw PRD
  — the interactive upstream skills are preconditions.
- The epic is parallel-front exploration with no story breakdown yet.
  Run `bmad-create-epics-and-stories` first.

## Design rationale

If you want to understand why the skill is shaped this way:

- [`docs/bmad-auto-design-intent.md`](../docs/bmad-auto-design-intent.md) — the
  operator-facing design intent (three modes, four phases, why SPIKES
  live inside Phase 1, etc.).
- [`docs/auto-skills-design.md`](../docs/auto-skills-design.md) — the
  architectural non-negotiables, especially the compaction-resilience
  story (why each story gets a fresh top-level Claude process via tmux).

**Helper binary (v5):** Phase 3 systems work — tmux session spawn,
poll-loop monitoring, HALT detection (sidecar-primary + grep
fallback with 3 structural guards), stall fingerprinting, adaptive
cadence derivation, and session kill — lives in
`scripts/bmad-auto-helper.py` (stdlib-only Python 3.11+, 5 CLI
subcommands: `spawn`, `monitor`, `halt-check`, `derive-cadence`,
`kill`). SKILL.md orchestrates via subcommand calls and branches on
the helper's 4-value `final_state` enum (`completed | halted |
stalled | timeout`). Extracted from SKILL.md prose on 2026-05-26 to
reduce token cost per poll cycle (~750K tokens saved per 5-story
run) and to make the polling logic executable rather than hand-
walked. Patterns referenced from `bmad-story-automator`'s
`tmux_runtime.py` (MIT). Closeout report:
`bmad-auto-helper-binary-extraction-final-review.md`.

## Known limitations

Two non-blocking limitations from the v4 validation cycle. None stop
the skill from running:

- HALT detection is sidecar-primary with capture-pane grep fallback.
  Implementation lives in the helper binary
  (`scripts/bmad-auto-helper.py`); see the helper test suite under
  `scripts/tests/` for coverage of both paths and the documented
  heuristic limitations.
- Quality-gate producer-side schemas (`bmad-testarch-trace`
  `gate-decision.json`, NFR report shape) are not pinned upstream
  in `bmad-testarch-*`. That upstream gap is unresolved, but it no
  longer silently corrupts our runs: three local defenses contain
  the blast radius. (1) Stage 4.a runtime-validates the trace JSON
  before trusting the verdict — drift HALTs loudly with an operator-
  actionable message rather than producing a wrong gate. (2) Stage
  4.b parses the NFR markdown exactly once into a canonical sidecar
  (`_bmad-output/.run-state/epic-K-nfr-decision.json`) that
  downstream stages consume; TEA reformats break the parser, not
  the digest, giving us a single point of repair. (3) Snapshot
  fixtures at
  [`../test-fixtures/testarch-outputs/`](../test-fixtures/testarch-outputs)
  pin known-good shapes (four `gate-decision-*.json` covering the
  full enum + three `nfr-assessment-*.md`); the fixture README
  defines a re-snapshot protocol tied to `/update-bmad` runs so
  drift gets caught at dev time, not at runtime. The upstream
  protection still matters in principle — a draft GitHub issue
  body lives at
  `bmad-testarch-schema-pinning.md`
  if we ever want to file it — but it's no longer the load-bearing
  mitigation.

The original G5v4 + G6v4 review-gate triage catalogued twelve items.
Post-cleanup, three were dropped as not-real-limitations (by-design
behaviors and an obsolete doc-update item), one (#9c
Codex non-git fallback) was patched in D13v4, and two more (polling
cadence and the HALT/STALL empirical constants coupled to it) were
resolved by the adaptive-cadence work: polling cadence is now derived
from epic story count at Stage 3 setup, and the STALL constants are
poll multipliers rather than absolute seconds, so they auto-tune across
the tier. The tier breakpoints themselves (1-3 → 45s, 4-7 → 30s,
8+ → 20s) remain an empirical choice. A further reduction landed on
2026-05-26: the `pause-before-this-story` v4.1 stop-condition was
removed entirely (rather than mitigated) because it inserted a third
HITL point mid-Phase-3, violating the bookend principle (start + end,
autonomous middle); the underlying need it addressed — surfacing
risky stories before Phase 2 launch — is now handled by the hybrid
Phase 1 hardening described above. Item 5 (Format A story-file
compat) resolved 2026-05-26 by adding a Stage 1.a per-story file
existence check that auto-invokes `bmad-create-story` for missing
files, and by documenting Stage 3's existing quick-dev delegation
contract — bringing the running count to two. The full triage lives in
`bmad-auto-validate-v4.md`'s
G5v4 and G6v4 Outcome blocks; the pause-feature removal is documented
in
`bmad-auto-phase1-hybrid-hardening.md`.

The structural blockers from the first real run (Stage 2.c
tracer-readiness gate, HALT false-positives, autonomous stall, Codex
non-git fallback) have all been patched.

### Historical follow-ups (2026-05-26)

Two follow-ups landed and are documented in source rather than
narrated here: (1) the `bad_spec` positive HALT fixture at
`../test-fixtures/halt-detection/trigger-bad-spec.txt`
closed the D1v4 trigger-coverage gap (all 7 substring trigger
classes now have a dedicated positive fixture); (2) a re-probe of
`codex exec --help` against codex-cli 0.124.0 surfaced a flag drift
(`--ask-for-approval never` is a `codex` top-level flag, not a
`codex exec` subcommand flag) and the two affected sites in
SKILL.md were swapped to `-c approval_policy=never`. The
"non-load-bearing" framing for item (2) was wrong — the re-probe
earned its keep by catching a real bug.

## After running `/update-bmad`

The `bmad-auto` skill is symlinked from `skills/bmad-auto/` into
`.claude/skills/bmad-auto/` so edits to the authored source flow
through automatically. The same applies to the `good-ideas` skill
(symlinked from `skills/good-ideas/`). The `/update-bmad` skill
rebuilds `.claude/skills/` from the canonical BMAD installation and
removes both symlinks in the process.

After every `/update-bmad` run, restore both symlinks with:

    python3 scripts/restore-bmad-auto-symlink.py

The script restores `bmad-auto` and `good-ideas` together (filename
predates the multi-skill split — not renamed to avoid scope creep).
Idempotent and stdlib-only — safe to run anytime.

## Where else to look

- [`SKILL.md`](../SKILL.md) — the authoritative runtime contract.
- [`scripts/bmad-auto-helper.py`](../scripts/bmad-auto-helper.py) —
  the v5 helper binary. Phase 3 spawn / monitor / halt-check /
  derive-cadence / kill all live here. Run `python3
  scripts/bmad-auto-helper.py --help` for the CLI surface.
- [`scripts/tests`](../scripts/tests) — pytest suite for the
  helper (53 stdlib-only unit tests) plus a four-variant e2e suite
  (`test_e2e_*.py`) that drives a real `claude` session inside tmux
  against a committed fixture epic. Run unit tests with `python3 -m
  pytest skills/bmad-auto/scripts/tests/` from the project root.
  E2E tests are opt-in: `-m e2e_fast` (T2 preflight HALT + T3 Phase 1
  FAIL HALT — minutes) or `-m e2e_slow` (T1 full epic + T4 Express
  consent — ~30–60 min each, real Claude API spend). See
  `scripts/tests/README.md` for
  per-variant status.
- [`tracer-readiness-check.md`](tracer-readiness-check.md) — the gate
  logic Phase 2.c runs.
- [`autonomous-mode-directives.md`](autonomous-mode-directives.md) —
  the verbatim directives embedded as the second message of each
  per-story spawn (the plain-prompt body the two-message protocol
  pastes after the short `/goal`).
- [`deferred-classifier.md`](deferred-classifier.md) — the classifier
  the Phase 4.d deferred-work delta uses.
- [`unknowns-hunter-prompt.md`](unknowns-hunter-prompt.md) — cold-load
  prompt for the Phase 1.e SPIKES unknowns-hunter subagent.
- [`edge-case-hunter-prompt.md`](edge-case-hunter-prompt.md) — cold-load
  prompt for the Phase 1.e edge-case-hunter subagent (wraps
  `bmad-review-edge-case-hunter` across the story list).
- [`deferred-upstream-tasks.md`](deferred-upstream-tasks.md) —
  trigger-activated upstream-merge task queue (BMAD-METHOD changes
  that need adopting once specific upstream conditions are met).
- [`bmad-auto-epic-spec-bundle-adoption.md`](bmad-auto-epic-spec-bundle-adoption.md) —
  forward-compat notes for BMAD-METHOD's epic SPEC-bundle direction
  (issue #2434).
- `BMAD-METHOD/src/bmm-skills/<skill-name>/SKILL.md` — the authoritative
  source for any sub-skill the conductor invokes. Useful if a sub-skill
  behaves unexpectedly; the SKILL.md tells you its contract directly.
- [`../test-fixtures/halt-detection/`](../test-fixtures/halt-detection) —
  fixture suite consumed by the helper's pytest suite (positive
  triggers, negative discrimination cases, sidecar exemplars). README
  in that folder documents the heuristic-baseline framing for the
  4-of-5 negative-grep "documented limitation" fixtures.
- [`../test-fixtures/g2v4-results/test-results.md`](../test-fixtures/g2v4-results/test-results.md) —
  the live-run findings from the v4 validation. Eleven deviations
  documented, all addressed or accepted as known limitations.

## Outstanding work

**Near-term (operational):** Smoke test + T1 e2e both passed on
2026-05-28 against the fixture epic at
`../test-fixtures/e2e/happy/` — full Phase 1–4 with
trace + NFR gates both PASS. v5 is **production-stable** under
Claude Code v2.1.153+. The only remaining e2e variant is T4 (Express
consent gate); see
`scripts/tests/README.md` for
status.

The T1 run surfaced one orchestrator bug that's now patched: against
Claude Code v2.1.153+, `cmd_spawn` needed boot-wait + workspace-
trust-prompt dismissal + paste-to-submit settle delays to avoid
stalling the per-story session at spawn time. SKILL.md Stage 3.2
documents the warmup contract; regression coverage in
`scripts/tests/test_spawn_two_message_split.py::test_cmd_spawn_applies_boot_wait_trust_dismiss_and_paste_settle_by_default`.

**Watch for upstream:** BMAD-METHOD architecture-skill streamline
flagged in the v6.8.0 roadmap (the "architecture spine" direction
BMadCode signaled on Discord, 2026-05-24). When it ships, the Stage
0.6 architecture-mode probe in [`SKILL.md`](../SKILL.md) starts
returning `architecture_has_express=true` against the updated
skill, which in turn unlocks the Stage 1.a auto-invoke path for
architecture. Nothing to do until then — the probe is already in
place and will activate on its own.
