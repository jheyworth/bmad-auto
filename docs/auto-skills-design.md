# `bmad-auto` — Architectural design (v4)

> The load-bearing design document for `bmad-auto`. The
> [docs/bmad-auto-design-intent.md](bmad-auto-design-intent.md) is the
> operator-facing intent; this doc is the architectural non-negotiables
> behind it. If a build task or SKILL.md edit contradicts this document,
> this document wins — flag it at the next Review Gate.
>
> **Companion doc:**
> [bmad-auto-design-intent.md](bmad-auto-design-intent.md). The per-sub-skill
> investigations and upstream design discussion that informed these docs were
> consolidated into `SKILL.md`.

---

## Redesign history

| Iteration | Date | What | Verdict |
|---|---|---|---|
| **v1** | 2026-05-22 | Two skills (`bmad-auto-prep` + `bmad-auto-dev`); `/goal`-driven autonomous loop; tmux multi-session for multi-epic parallelism | Naive — didn't reckon with auto-compaction; `/goal` at epic scope is compaction-vulnerable |
| **v2** | 2026-05-23 | Two skills; skill-driven loop (no `/goal`); no tmux; single epic / single session | Compaction-aware in principle, but **structurally broken**: `Skill` tool runs inline in the orchestrator's session, accumulating context |
| **v3** | 2026-05-24 | **One skill** with mode-detection (prep / dev / verify); **tmux per story**; **`/goal` per story**; dual-format tracer-readiness check | Correct topology, but **scoped wrong**: modal-only workflow forced operator into state-machine role; SPIKES handling underspecified; tests-first not wired; quality gates absent |
| **v4** | 2026-05-25 | One skill, three workflow modes (**Express / Headless / Guided**); four phases (per-epic hardening / tracer-bullet / autonomous fanout / quality-gated end); **conductor pattern** — auto-invokes upstream BMAD skills (`bmad-spec`, `bmad-sprint-planning`, `bmad-create-story`, `bmad-testarch-atdd`, etc.); **tests-first via per-story ATDD**; **quality gates** (`bmad-testarch-trace` + `bmad-testarch-nfr`) at Phase 4; **SPIKES live inside Phase 1 hardening** (as Stage 1.e checklist + Stage 1.f spike triage); auto-spawn `bmad-retrospective` | Aligned with BMadCode's three-mode framework + Alex Verhovsky's per-epic execution pipeline. Superseded by v4.1 below. |
| **v4.1** | 2026-05-26 | v4 carryover, except: **Phase 1 hardening collapsed into a single hybrid Stage 1.e** — parallel Task subagents (unknowns-hunter using the SPIKES method + edge-case-hunter wrapping `bmad-review-edge-case-hunter` across the story list) feed a unified operator triage table (resolve-now / defer-to-digest / split-off); optional `/good-ideas` inline escalation per finding before deciding; findings JSON (`epic-K-phase1-findings.json`) replaces the legacy `epic-K-spike-log.md`. Also **removed**: the v4.1 `pause-before-this-story:` mid-flow stop-condition (Stage 3.0 pre-check + Stage 3.C.4 PAUSE exit) — violated the HITL-bookend principle (start + end, autonomous middle); its underlying need is now subsumed by hybrid hardening. | Restores design alignment with the bookend principle while closing the prior internal-story-quality and idea-hardening gaps. Superseded by v5 below. Documented in bmad-auto-phase1-hybrid-hardening.md. |
| **v5 (current)** | 2026-05-26 | Helper binary extraction. Stage 3.4 polling / HALT-detection / stall-fingerprinting logic (~150 lines of LLM prose) moved from SKILL.md into a stdlib-only Python 3.11+ helper at [`skills/bmad-auto/scripts/bmad-auto-helper.py`](../scripts/bmad-auto-helper.py), invoked as a single bash call per poll cycle and emitting a JSON status block with `final_state` ∈ {`completed`, `halted`, `stalled`, `timeout`}. Helper carries a 30-test pytest suite in `skills/bmad-auto/scripts/tests/` (all passing). SKILL.md shrank 1517 → 1404 lines net. Pattern ported from `bmad-story-automator`'s `tmux_runtime.py` (MIT-licensed prior art). | Strengthens non-negotiable #3 (orchestrator session stays radically lean) — token cost per poll cycle drops from N tokens of LLM-prose reasoning to 1 bash call returning a small JSON block. **Current truth.** |

The v3 modal design was scoped to validate-then-execute as separate operator-driven commands. v4 keeps the modal granularity (as Guided opt-in) but adds Express (chained default) and Headless (best-effort autonomous) modes, plus folds in tests-first and quality gates that v3 missed.

---

## Why this design exists

`bmad-auto` is a deliberate counter-demonstration to a wavering architectural premise in the BMAD ecosystem.

[`bmad-automator`](https://github.com/bmad-code-org/bmad-automator) is a heavyweight Python orchestrator — per-step tmux sessions, atomic markdown state files, policy snapshots, retry/escalation rules. Its author has publicly weighed whether all that machinery is necessary:

> *"I'm actually starting to feel the automator might not be necessary if Claude also can function through context compaction as well as Codex does."* — bmad-automator author, Discord, 2026-05-23

**Our position:** letting auto-compaction run during autonomous code execution is a category mistake. v4 demonstrates a middle path — lighter than `bmad-automator`'s machinery, but deliberately *more* careful than "trust compaction" — that solves the problem at the right level of complexity.

v4 also implements Alex Verhovsky's per-epic execution pipeline natively. Where v3 was an orchestrator-shaped skill, v4 is a **conductor** that auto-invokes the other BMAD skills (`bmad-spec`, `bmad-create-story`, `bmad-testarch-atdd`, `bmad-quick-dev`, `bmad-testarch-trace`, `bmad-retrospective`, etc.) at the right boundaries with the right HITL/autonomous discipline.

---

## Load-bearing principles

### Principle 1 — Compaction is the enemy

Auto-compaction is *lossy summarization*. It is tuned for "keep the conversation coherent," not "preserve architectural decisions verbatim across hours of code work." For autonomous code execution it breaks in predictable, specific ways: tracer drift, loopback amnesia, directive erosion, subagent compression compounding, non-deterministic timing.

The "compaction is good enough" bet is right *for chat*. It is wrong for autonomous code work where architectural decision-chain integrity has to be preserved exactly.

### Principle 2 — HITL distribution matches Alex Verhovsky's pattern

> *"The weight of HITL moves to the beginning and the end of the epic. Shoot the first tracer bullet through the target, and the rest of it just falls into place."* — Alex Verhovsky, Discord 2026-05-23

v4 implements this concretely:
- **Phase 1 (HITL):** per-epic hardening — hybrid Stage 1.e (parallel unknowns-hunter + edge-case-hunter scan, unified operator triage, optional `/good-ideas` escalation; per v4.1)
- **Phase 2 (HITL):** tracer-bullet via interactive `bmad-quick-dev` on K-1
- **Phase 3 (autonomous):** dev fanout for K-2..K-N
- **Phase 4 (HITL):** quality gates + digest + retrospective

The autonomous middle is bounded by HITL bookends. HITL inside autonomous Phase 3 only fires on HALT — by design.

### Principle 3 — Tests-first is architecturally enforced

BMAD is tests-first (evidence). `bmad-dev-story` explicitly says: *"Write FAILING tests first... Confirm tests fail before implementation."* But `bmad-testarch-atdd` (the explicit red-phase scaffold producer) is currently orphaned from `bmad-story-automator`.

v4 fixes this: ATDD runs per-story BEFORE quick-dev (Phase 2a + Phase 3.b). Red tests are externally auditable artifacts (`atdd-checklist-K-<storyId>.md`), not implicit dev-story RGR outputs. Tracer-readiness gate (Phase 2c) and quality gate (Phase 4a) enforce the discipline.

### Principle 4 — Conductor, not monolith

`/bmad-auto` is a thin orchestrator that auto-invokes the existing BMAD skills at the right boundaries. Heavy lifting lives in the invoked skills (`bmad-spec` for distillation, `bmad-create-story` for story creation, `bmad-testarch-atdd` for red tests, `bmad-quick-dev` for implementation, `bmad-testarch-trace` for quality gates, `bmad-retrospective` for lessons-learned). What's unique to `/bmad-auto`:

- Per-epic hybrid hardening (Phase 1 Stage 1.e — parallel SPIKES + edge-case-hunter scan with unified triage) — no other skill does this
- Per-story tmux fanout topology (Phase 3) — preserved from v3
- Codex adversarial review against the per-epic diff (Phase 4c)
- Sidecar-driven state and digest composition

---

## How v4 achieves compaction-resilience (extends v3)

The v3 insight stands: **the unit of fresh context must be a fresh top-level Claude process, not a `Skill`-tool invocation.** Skill calls run inline in the orchestrator's session and accumulate context. Only spawning a separate `claude` process (via tmux) gives genuinely isolated context.

v4 preserves v3's mechanics and extends them:

- **Each non-tracer story** in Phase 3 runs in its own tmux session — a fresh top-level `claude --dangerously-skip-permissions` process. The per-story `/goal` directive embeds ATDD-then-quick-dev-then-automate-then-code-review as the chained per-story workflow. Quick-dev's internal subagents work normally inside that session because it's top-level.
- **The tracer (Phase 2 in Express)** runs **direct in-session** with the operator engaging interactively. Topology choice rationale: tracer is heavy-HITL by design; tmux-spawning would lose the natural conversation flow. Express's session lifetime is bounded by Phase 2's interactive scope plus the Phase 3 loop's polling overhead — well under any compaction threshold.
- **The tracer in Headless mode** collapses into Phase 3's per-story fanout (tracer becomes story #1). No special HITL hooks; if quick-dev raises `intent_gap`, Stage 3.4 capture-pane HALT detection catches it and the run exits cleanly. Headless never blocks on operator input.
- **The orchestrator session** carries only: tmux session names, one-line per-story status logs, sidecar file paths, and gate decisions. Its context grows linearly and slowly — for a typical 5–7 story epic, ~2–4k tokens of state, well under compaction threshold.
- **Codex adversarial review** (Phase 4c) catches drift that survived per-story isolation. Different model family, clean context.

The `/goal`-at-story-scope rationale from v3 still holds: bad at the epic level (long session, compaction fires), fine at the story level (short session, compaction never fires).

**(v5 NEW) LLM-orchestrator-plus-helper-binary pattern.** v5 extends compaction-resilience further by extracting deterministic, mechanical logic (Stage 3.4 poll-loop, HALT-string detection, stall fingerprinting) from LLM prose into a stdlib-only Python helper at [`skills/bmad-auto/scripts/bmad-auto-helper.py`](../scripts/bmad-auto-helper.py). The orchestrator session no longer reasons through the polling state machine token-by-token; it issues one bash call per cycle and parses a small JSON status block. Pattern attribution: ported from `bmad-story-automator`'s `tmux_runtime.py` (MIT-licensed prior art for the same shape — LLM conductor + Python runtime helper). The principle: anything mechanical and testable belongs in a helper binary, not in LLM context.

---

## The three workflow modes

| Mode | Flag | HITL distribution | Typical use |
|---|---|---|---|
| **Express** | (default — no flag) | Phase 1 + Phase 2 + Phase 4 | First-time runs against a well-prepared epic |
| **Headless** | `--headless` | Phase 4 digest only (or post-hoc) | Re-runs after HALT recovery; trivial epics; walk-away operation |
| **Guided** | `--prep` / `--verify` / `--dev` | Phase-by-phase operator-invoked | Operator wants explicit modal granularity (current v3 behavior) |

Per BMadCode's three-mode framework (Discord 2026-05-24): *"all workflows will support headless mode, express mode, and full guided modes."* v4 aligns.

---

## Non-negotiables

These rules follow from the principles. Build tasks must respect them; any task that would violate one must be revised or rejected at a Review Gate.

1. **Each non-tracer story executes in its own fresh top-level Claude process.** No exceptions in Phase 3. A spawned tmux + `claude --dangerously-skip-permissions` session per story.

2. **`/goal` is used per-story, never per-epic.** Story-scoped `/goal` sessions are short enough that directive erosion doesn't happen.

3. **Orchestrator session stays radically lean.** Reads sprint-status fresh per iteration; carries one-line statuses only; never accumulates per-story implementation context.

4. **Autonomous-mode directives travel with each `/goal` invocation.** Not stored once in long-lived context. `references/autonomous-mode-directives.md` is read by the orchestrator per iteration and embedded into each per-story `/goal` condition.

5. **Mode signposting before irreversible work.** Operator is always told which mode is being entered and what's about to happen. Single consent gate for `--dangerously-skip-permissions` posture.

6. **Single epic per skill invocation.** No multi-epic fan-out from within the skill. Operator-driven coarse parallelism (separate `/bmad-auto --epics K` terminals) is the parallelism story.

7. **Codex adversarial review at end of epic (Phase 4c).** Different model family, clean context. Skipped on HALT-exit and when codex is unavailable.

8. **(v4 NEW) Tests-first via ATDD per-story.** `bmad-testarch-atdd` runs before `bmad-quick-dev` in Phase 2a (tracer) and Phase 3.b (every non-tracer story). Red tests are externally auditable artifacts. `--skip-atdd` is an explicit override for docs-only / trivial-refactor epics, not the default.

9. **(v4 NEW) Phase 4 quality gates feed the auto-merge decision.** `bmad-testarch-trace` produces PASS / CONCERNS / FAIL / WAIVED. `bmad-testarch-nfr` runs conditional on implementation evidence. Combined gate logic determines digest content and auto-merge eligibility.

10. **(v4 NEW) Per-epic SPIKES live inside Phase 1.** Upstream skills (Brief / PRD-or-SPEC / UX / Architecture / Epics) surface assumptions and open_questions but do not orchestrate spike work. Per-epic spike triage (spike / defer / block) happens in `/bmad-auto` Phase 1f. The triage persists to `epic-K-spike-log.md` for resumable runs.

11. **(v4 NEW) Input contract is permissive; auto-invoke missing autonomous upstream.** If `sprint-status.yaml` is missing → auto-invoke `bmad-sprint-planning`. If SPEC missing but PRD exists → offer `bmad-spec`. If K's stories not detailed → auto-invoke `bmad-create-story`. HALT only on missing interactive-only upstream (PRD, UX, Architecture, create-epics-and-stories).

12. **(v4 NEW) Express mode auto-spawns `bmad-retrospective` at Phase 4f.** Heavy interactive, aligned with Alex's "lessons-learned/correct-course" end-of-epic pattern. Conditional `bmad-correct-course` at 4g if retrospective Step 8 emits significant-discoveries signal.

---

## What this rules out (explicitly)

To prevent regression by future maintainers:

- ❌ `/goal` at epic scope (compaction-vulnerable directive container)
- ❌ Multi-epic execution within one skill invocation
- ❌ Parallel story execution within an epic (intra-epic dependencies make this unsafe; quick-dev handles within-story parallelism via subagents)
- ❌ `Skill`-tool invocations of `bmad-quick-dev` from the orchestrator (those run inline in orchestrator context — exactly what we're avoiding for Phase 3)
- ❌ `Agent`-tool invocations of `bmad-quick-dev` (the agent-spawned subagent can't nest further; quick-dev's own research/implement/review subagents wouldn't work)
- ❌ External state files for resume (we accept "if it crashes, re-run from sprint-status state")
- ❌ `claude -p` in shipped solutions (project-wide constraint)
- ❌ **(v4 NEW)** Per-epic SPIKES delegated to upstream (corrected from earlier design intent iterations — SPIKES live in Phase 1)
- ❌ **(v4 NEW)** Skipping ATDD by default (tests-first is the architectural commitment; `--skip-atdd` is an explicit operator override)
- ❌ **(v4 NEW)** `/bmad-auto` intercepting quick-dev's `intent_gap` flow (quick-dev's revert + replan + 5-iteration-limit machinery is the authoritative handler; the orchestrator observes completion only)

---

## Architecture artifact contract (tracer-readiness)

The tracer-readiness check (Phase 2c) validates that the K-1 tracer story has produced enough architectural decision-evidence to launch the autonomous Phase 3 fanout. The contract is **dual-format**: the canonical per-epic-distillation pattern, and the small-project equivalent that substitutes the whole-project architecture artifact.

**Format A — canonical:**
- `sprint-status.yaml` shows `<K>-1-<key>: done`
- `_bmad-output/implementation-artifacts/epic-K-micro-prd.md` with required sections
- `_bmad-output/implementation-artifacts/epic-K-micro-architecture.md` with required sections

**Format A-equivalent — small-project fallback:**
- `sprint-status.yaml` shows `<K>-1-<key>: done`
- No per-epic micro-files produced (small single-epic projects often skip per-epic distillation)
- The whole-project `{planning_artifacts}/architecture.md` carries the architectural decision-evidence the tracer needs

Both formats pass the same downstream contract. Format A-equivalent was validated as a real-world need during G3v4 — single-epic projects routinely produce a flat architecture.md without per-epic micro-distillation, and the tracer-readiness gate must accept that posture rather than HALT spuriously.

### Why this is no longer "tri-format"

An earlier iteration of this contract hedged against a hypothesized "Format B" — a per-epic folder layout (`_bmad-output/implementation-artifacts/epics/K/stories/*.md` plus `epics/K/solution-design.md`) that BMadCode was assumed to be moving toward. A fresh BMAD-METHOD v6.8.0 clone (2026-05-26) returns **zero hits** for `solution-design` or `solution_design` anywhere in `src/`, and `bmad-create-architecture` still produces a single flat `{planning_artifacts}/architecture.md`. The per-epic folder structure was speculation that never landed.

The actual upstream signal worth hedging against is **architecture spine** — a streamlined single `architecture.md` artifact, mentioned in BMadCode's Discord 2026-05-24 and reinforced in the v6.8.0 roadmap "Next:" item: *"Architecture, story, dev, review skills get the same streamline."* That direction reduces the architecture surface area, it does not fan it out into per-epic folders. Stage 0.6's architecture-mode probe in [SKILL.md](../SKILL.md) hedges against the spine streamline, not the (non-existent) per-epic folder direction.

Paired with this update, [`skills/bmad-auto/references/tracer-readiness-check.md`](../references/tracer-readiness-check.md) has been stripped of Format B clauses and reframed as the same dual-format contract (Format A + Format A-equivalent) described here.

---

## (v4 NEW) Quality gate architecture

Phase 4 produces machine-readable gate decisions that feed the digest and the auto-merge contract:

```
trace.gate_status: PASS | CONCERNS | FAIL | WAIVED   (from bmad-testarch-trace)
nfr.gate_status:   PASS | CONCERNS | FAIL            (from bmad-testarch-nfr, conditional)

IF trace == FAIL                                  → BLOCK merge, escalate
ELSE IF trace == CONCERNS AND nfr == FAIL         → BLOCK, escalate
ELSE IF (trace == PASS or CONCERNS) AND nfr ok    → proceed; operator decides at digest
ELSE IF trace == WAIVED                           → proceed with documented risk
```

The gates run automatically. Their PASS / CONCERNS / FAIL outcomes are surfaced in the digest. The operator reviews and decides — `/bmad-auto` doesn't auto-merge.

Conditional NFR audit: `bmad-testarch-nfr` runs only when implementation evidence exists (CI test results, security scans, performance metrics, logs, monitoring data). For epics that don't touch NFR-affecting code, NFR audit is skipped and the digest reports N/A.

---

## (v4 NEW) Pipeline conductor architecture

`/bmad-auto` invokes other BMAD skills at specific boundaries. The invocation contract differs per skill — some are headless-capable, some are interactive-only, and `/bmad-auto`'s mode (Express / Headless / Guided) interacts with each skill's interactivity profile:

| Skill | Boundary | Invocation |
|---|---|---|
| `bmad-spec` | Phase 1a auto-invoke if missing | Headless mode (JSON status block) |
| `bmad-sprint-planning` | Phase 1a auto-invoke if missing | Fully autonomous |
| `bmad-create-story` | Phase 1a, 1g, 3.a auto-invoke for missing/thin stories | Minimal interactive — auto-discovers from sprint-status |
| `bmad-check-implementation-readiness` | Phase 1b (optional, Express prompts) | Step-based interactive |
| `bmad-testarch-test-design` | Phase 1c (optional system-level) | Interactive when ambiguous |
| `bmad-testarch-atdd` | Phase 2a (tracer), Phase 3.b (per-story) | Interactive when ambiguous; tmux-spawned in Phase 3 |
| `bmad-quick-dev` | Phase 2b (tracer direct-in-session), Phase 3.c (per-story tmux) | Heavy interactive on tracer; autonomous in tmux |
| `bmad-testarch-automate` / `bmad-qa-generate-e2e-tests` | Phase 3.d coverage expansion | Autonomous; non-blocking |
| `bmad-code-review` | Phase 3.e | Autonomous |
| `bmad-testarch-trace` | Phase 4a quality gate | Autonomous |
| `bmad-testarch-nfr` | Phase 4b NFR audit (conditional) | Autonomous |
| `bmad-retrospective` | Phase 4f auto-spawn (Express) | Heavy interactive (party-mode) |
| `bmad-correct-course` | Phase 4g conditional auto-prompt | Interactive |

**Operator-on-demand from Phase 1.e (hybrid hardening — for triage escalations):** `bmad-create-architecture`, `bmad-agent-architect`, `bmad-technical-research`, `bmad-domain-research`, `bmad-agent-pm`, `bmad-ux`, `bmad-tea` (Murat), `bmad-review-edge-case-hunter`, `/good-ideas`.

---

## Relationship to `bmad-automator`

`bmad-automator` is not a competitor — same problem, different point on the architecture-complexity tradeoff curve. v4 here **adopts** their tmux-per-work-unit pattern (we use it at story granularity) and adds layers they don't have:

| Concern | `bmad-automator` | `bmad-auto` (v4) |
|---|---|---|
| Fresh context per work unit | Per-step tmux + `claude --dangerously-skip-permissions` | Per-story tmux + `claude --dangerously-skip-permissions` |
| Autonomous-loop primitive inside each spawned session | Step-file prompt iteration | `/goal` with story-scoped condition embedding the 5-step per-story workflow |
| State persistence | External markdown + JSON state files | Sidecar files in `_bmad-output/.run-state/` + sprint-status as source of truth |
| Resume after crash | Yes (atomic state files) | Yes (sprint-status persists across re-invocations; `epic-K-phase1-findings.json` persists Stage 1.e triage decisions) |
| Tracer-readiness pre-check | No (assumes upstream is correct) | Yes (Phase 2c, dual-format: Format A + A-equivalent) |
| Codex adversarial review | No (verification-focused review only) | Yes (Phase 4c, with D3-corrected `--base <branch>` invocation) |
| Multi-mode (HITL prep / autonomous dev / verify) | No (single autonomous orchestration) | Yes (Express / Headless / Guided) |
| **Tests-first ATDD** | No | **Yes (v4) — per-story ATDD before quick-dev** |
| **Quality gates** | No | **Yes (v4) — trace + NFR feeding digest** |
| **Conductor pattern** | Custom Python orchestration | **Yes (v4) — auto-invokes BMAD skills at boundaries** |

If our bet is wrong — if compaction-resilience requires more than per-story isolation plus careful orchestration — `bmad-automator` is the fallback.

---

## Convergence with Alex Verhovsky's pipeline (2026-05-23 Discord)

v3 had four convergent points. v4 implements Alex's per-epic execution pipeline natively (steps 9–14 of his pipeline) and extends the convergence:

- **Tracer-bullet story per epic.** Alex's deviation 6a — *"pull uncertainty leftward; every epic starts with a tracer-bullet story that forces the hard decisions early."* Our Phase 1 + Phase 2 implement this. Convergent.
- **Just-in-time story authoring within an epic.** Alex's deviation 7 — *"detailed stories only for the first epic; the story words can wait."* v4 auto-invokes `bmad-create-story` for epics beyond the first (Phase 1a + 1g + 3.a). Convergent.
- **Different LLM for review than for generation.** Alex's review policy — Codex review at Phase 4c uses a different model family. Convergent.
- **Parallel-across-epics, sequential-within-epic.** Operator-driven coarse parallelism (two `/bmad-auto` terminals). Aligned.
- **(v4 NEW) Per-epic execution = Phase 1 hardening → tracer-bullet → autonomous rest → HITL review → lessons-learned.** Alex's exact execution sequence is the v4 Express phase structure. We ARE Alex's execution side.
- **(v4 NEW) HITL concentrated at beginning + end of epic.** Alex's load-bearing pattern. v4 phases 1/2 (heavy HITL) + phase 4 (digest + retrospective HITL) bracket the autonomous middle (phase 3).

---

## What this design contributes that the broader BMAD/AI-coding world hasn't articulated

- **Compaction as a fidelity threat to autonomous code work.** Neither Alex nor BMadCode has surfaced this. `bmad-automator`'s author was *moving toward* a position that depends on compaction being safe, which it isn't for this use case.
- **The corollary: the unit of context-isolation matters and "fresh subagent" isn't always enough.** `Skill`-tool inline execution looks like isolation but isn't. `Agent`-tool subagents are fresh but can't nest, so they break tools (like quick-dev) that rely on internal subagent delegation. **Only a fresh top-level Claude process gives the isolation property AND preserves nesting.**
- **(v4 NEW) Tests-first via ATDD pre-step is architecturally enforceable.** `bmad-dev-story` has tests-first inside its RGR loop, but ATDD as a separate auditable pre-step is currently orphaned in BMAD. v4 wires ATDD into the per-story flow as a first-class step, making the discipline externally auditable rather than dev-story-implicit.
- **(v4 NEW) Per-epic SPIKE triage as a phase, not a pre-condition.** Upstream BMAD skills surface assumptions / open_questions but don't orchestrate spike work. v4 makes per-epic spike triage a load-bearing Phase 1 mechanic with persistent triage logs, integrated with the SPIKES checklist that routes to specific BMAD investigation skills.
- **(v4 NEW) Quality gates feeding auto-merge.** Trace + NFR gate decisions are machine-readable signals that the digest surfaces to operator decisions. The architecture commits to gate-driven progression rather than vibes-driven approval.

---

## Provenance

- Discord context from `bmad-code-org/bmad-automator` author, 2026-05-23 (compaction wavering)
- Alex Verhovsky's BMAD-deviation talk highlights, 2026-05-23 (convergent patterns)
- BMadCode three-mode framework + bmad-spec announcement, 2026-05-24 (architecture-spine streamlining, frontmatter-based tracking, adaptive flows)
- Alex Verhovsky's full per-epic execution pipeline, 2026-05-25 (heavy-HITL tracer-bullet + autonomous rest + HITL review + lessons-learned)
- v4 scope reset and design rewrite, 2026-05-25 (after operator corrected misframing of SPIKES as upstream-delegated)
- Investigation docs 2026-05-25 (5 docs covering sub-skill contracts, upstream skills, pipeline skills, architecture, testarch family)
- v4.1 Phase 1 hybrid-hardening pivot, 2026-05-26 (combined SPIKES + edge-case-hunter into a single parallel-scan Stage 1.e with unified triage; removed the mid-flow `pause-before-this-story:` stop-condition for violating the HITL-bookend principle). Documented in `bmad-auto-phase1-hybrid-hardening.md`.
- Related references:
  - [docs/bmad-auto-design-intent.md](bmad-auto-design-intent.md) — operator-facing intent (v2)
  - [skills/bmad-auto/references/tracer-readiness-check.md](../references/tracer-readiness-check.md) — authoritative tracer-readiness contract (dual-format: Format A + A-equivalent)
  - [skills/bmad-auto/references/deferred-classifier.md](../references/deferred-classifier.md) — Phase 4d classifier algorithm
  - [bmad-automator](https://github.com/bmad-code-org/bmad-automator) — the heavyweight alternative this design counter-demonstrates against
