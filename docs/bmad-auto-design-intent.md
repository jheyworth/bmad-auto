# `/bmad-auto` — Design intent (2026-05-25 v2, post-investigation)

> **2026-05-26 amendment — Phase 1 hybrid-hardening pivot.** Phase 1's
> mechanics changed: the standalone SPIKES checklist (Stage 1.e) +
> per-epic spike triage (Stage 1.f) described throughout this doc were
> collapsed into a single hybrid Stage 1.e that runs SPIKES and
> `bmad-review-edge-case-hunter` as parallel Task subagents feeding a
> unified operator triage table, with optional `/good-ideas` inline
> escalation per finding. The v4.1 `pause-before-this-story:`
> stop-condition (Stage 3.0 / 3.C.4) was removed in the same pass for
> violating the HITL-bookend principle. The strategic claims in this
> doc — SPIKES live inside Phase 1, per-epic spike triage as a phase
> rather than a pre-condition, HITL bookends with autonomous middle —
> remain accurate; the mechanic of how SPIKES + triage execute is the
> only thing that shifted. Full record:
> bmad-auto-phase1-hybrid-hardening.md.
> [`docs/auto-skills-design.md`](auto-skills-design.md) carries the v4.1
> Redesign-history row.
>
> **Authoritative going forward.** Supersedes prior intent in
> [skills/bmad-auto/SKILL.md](../SKILL.md) and
> [docs/auto-skills-design.md](auto-skills-design.md) where they conflict.
>
> **Source of truth:** the per-sub-skill investigations and the upstream design
> discussion (Alex Verkhovsky's tracer-bullet pipeline; BMadCode's three-mode
> framework) that informed this doc were consolidated into `SKILL.md` and the
> sections below; they are not shipped as separate files.
>
> **Earlier revisions** (in this doc's git history) had three significant
> errors which this v2 fixes:
> 1. Treated SPIKES as belonging upstream — wrong, they live inside `/bmad-auto` Phase 1
> 2. Framed Phase 1 as light handoff — wrong, it's the per-epic hardening phase
> 3. Missed tests entirely — BMAD is tests-first; ATDD belongs per-story

---

## Headline

`/bmad-auto` is **the per-epic execution conductor** implementing Alex Verhovsky's pipeline:

> *"Take epic 1, create an EPIC spec that includes a story breakdown. Run quick-dev on story 1-1 with heavy HITL, trying to resolve all the unknowns for the rest of the epic. Run the rest of the epic — autonomously, if possible. HITL review the result. Run some sort of lessons-learned/correct course."*

It takes a hardened epic (with upstream Brief / PRD-or-Spec / UX / Architecture / epics.md / sprint-status.yaml already finalized), does **per-epic hardening** (the SPIKES work), drives the **tracer-bullet** through `bmad-quick-dev`, runs **autonomous fanout** for the rest of the epic, and closes with **quality gates + digest + retrospective**.

The skill supports **three workflow modes** per BMadCode's framework:

| Mode | Flag | HITL distribution |
| --- | --- | --- |
| **Express** | (default) | HITL at Phase 1 (per-epic hardening + SPIKES) + Phase 2 (tracer-bullet quick-dev interactive) + Phase 4 (digest review + retrospective). Autonomous middle (Phase 3 dev-fanout). |
| **Headless** | `--headless` | Phase 1 / 2 / 3 all autonomous. Phase 4 only surfaces if quality gates fail or operator returns. Quick-dev's intent_gap escalation still pulls operator in if it fires. "Best-effort autonomous." |
| **Guided** | `--prep` / `--verify` / `--dev` | Modal opt-in — operator invokes each phase separately. Current SKILL.md modal behavior preserved. |

---

## Express mode — the four phases

### Phase 1 — Per-epic hardening (heavy HITL)

This is where SPIKES happen. The operator drives; `/bmad-auto` structures.

#### 1a. Input validation + auto-invocation of missing upstream

- Validate presence of: `brief.md`, PRD or `SPEC.md`, UX `DESIGN.md` + `EXPERIENCE.md`, `architecture.md`, `epics.md`, `sprint-status.yaml`
- For missing items, offer to fix inline:
  - SPEC missing but PRD exists → offer to auto-invoke `bmad-spec` (has headless mode)
  - `sprint-status.yaml` missing → auto-invoke `bmad-sprint-planning` (fully autonomous)
  - Epic K's stories not broken down → auto-invoke `bmad-create-story` (auto-discovers from sprint-status)
  - `architecture.md` missing → HALT and tell operator to run `bmad-create-architecture` (interactive-only; no headless mode in source yet — see architecture investigation)
  - PRD missing → HALT and tell operator to run `bmad-prd`
- **Do not blindly HALT on missing upstream — offer to fix it inline where the upstream skill supports auto-invocation.**

#### 1b. Optional Phase 3→4 readiness gate

- Offer to invoke `bmad-check-implementation-readiness`
- Express default: prompt `Run bmad-check-implementation-readiness? [Y/n]` (Y recommended)
- On NOT READY → HALT; on NEEDS WORK → surface report, ask to proceed at risk; on READY → proceed
- Headless default: skip (operator trusts state); `--check-readiness` overrides

#### 1c. (Optional) System-level test plan

- Offer to invoke `bmad-testarch-test-design` (system-level mode) if no `test-design-architecture.md` exists yet
- Produces: `test-design-architecture.md`, `test-design-qa.md`, `test-design-handoff.md`
- Non-blocking; operator can defer

#### 1d. Unknown extraction for epic K (programmatic, low-HITL)

- Walk SPEC's `companions: []` frontmatter to load adopted UX/architecture artifacts
- Mechanically extract from upstream artifacts touching epic K:
  - `[ASSUMPTION]` tags in `brief.md`, `DESIGN.md`, `EXPERIENCE.md`
  - SPEC's `assumptions[]` and `open_questions[]` touching K's CAP-N's (filter via Spec's capability→epic mapping)
  - `epics.md` Step-4 validation gaps marked against K
  - `architecture.md` Gap Analysis items (Critical/Important) affecting K — read as prose; no structured array
- Present consolidated report to operator: *"Here's what's still uncertain about epic K"*

**1e. SPIKES checklist (current 4-question mechanic + extensions)**
- Each question non-blocking; a "no" routes to the right BMAD skill as an action item
  - **(1) Architectural unknowns** → `bmad-create-architecture` (interactive) / `bmad-agent-architect` (talk to Winston)
  - **(2) Integration unknowns** → `bmad-technical-research`
  - **(3) Domain unknowns** → `bmad-domain-research` / `bmad-prd` / `bmad-ux`
  - **(4) Spec gaps** → `bmad-spec` Validate mode against K's CAP-N's (NEW)
  - **(5) UX-DR precision** → `bmad-ux` Validate mode (NEW)
  - **(6) Test strategy** → `bmad-tea` (talk to Murat) for risk-based test strategy consultation (NEW)
  - **(7) Synthesis check** — *"Could a teammate sketch the implementation on a whiteboard?"*
- Operator collects action items; chooses to address now (exit and re-invoke) or proceed inline

**1f. Per-epic spike triage**
- For each unresolved unknown from 1d + 1e, the operator classifies:
  - **Spike** — route to investigation skill (operator exits, runs skill, returns)
  - **Defer** — log decision in `epic-K-spike-log.md`, proceed at risk
  - **Block** — HALT until resolved; cannot proceed
- Spike-triage record persists; resumable runs respect prior decisions

**1g. Tracer-bullet readiness**
- Confirm story K-1 exists in `epics.md` and `sprint-status.yaml`
- Check tracer story has functional ACs (not just placeholders)
- If missing/thin, auto-invoke `bmad-create-story` for K-1 (operator engages briefly via auto-discover)
- Phase 1 complete → transition to Phase 2

---

### Phase 2 — Tracer-bullet (heavy HITL)

The final SPIKE for epic K. Resolves all remaining unknowns by executing story K-1 with operator engagement.

**Topology:** direct in-session. `/bmad-auto`'s instructions invoke `bmad-testarch-atdd` then `bmad-quick-dev` in the same Claude Code session. Operator interacts with quick-dev's prompts directly.

**2a. ATDD red-phase scaffolds**
- Invoke `bmad-testarch-atdd` against story K-1
- Produces:
  - `atdd-checklist-K-1.md` — red-phase test scaffold + implementation checklist
  - Generated red test files (E2E/API/Component skeletons per stack)
  - Fixture stubs and helper signatures
- Operator may engage if ACs are ambiguous; otherwise autonomous

**2b. Tracer implementation via quick-dev**
- Invoke `bmad-quick-dev` against story K-1
- Heavy HITL — operator and quick-dev together:
  - Make red tests green
  - Produce `epic-K-micro-prd.md` + `epic-K-micro-architecture.md` (Format A) — or, for small single-epic projects, rely on the whole-project `architecture.md` + SPEC/PRD as Format A-equivalent
  - Surface and resolve architectural decisions for the rest of epic K
- Quick-dev's internal `intent_gap` handling (revert + replan + iteration limit) stays in quick-dev's flow — `/bmad-auto` does NOT intercept (rationale)

**2c. Tracer-readiness gate**
- Single gate: `references/tracer-readiness-check.md` logic
- Checks: sprint-status K-1 = `done` + micro-PRD/architecture (or Format A-equivalent whole-project `architecture.md`) present with all required sections + red tests pass
- PASS → continue to Phase 3
- FAIL → HALT with specific failure message (per `tracer-readiness-check.md` failure modes) + remediation directive: *"Either fix manually and re-invoke `/bmad-auto`, or resume `/bmad-quick-dev` on K-1."*

**Architecture-artifact contract (note).** Earlier revisions of this design hedged against a hypothetical "Format B" per-epic folder structure (`epics/<K>/solution-design.md`). Fresh evidence (BMAD-METHOD v6.8.0 clone + roadmap, 2026-05-26) confirms no upstream basis — the v6.8.0 roadmap's "Next:" item is architecture-spine streamlining, not per-epic folders. The dual-format contract is now canonical: **Format A** (per-epic `epic-K-micro-prd.md` + `epic-K-micro-architecture.md`) and **Format A-equivalent** (whole-project `architecture.md` + SPEC/PRD as fallback for small projects). See [auto-skills-design.md § Architecture artifact contract (tracer-readiness)](auto-skills-design.md) for the full rationale.

---

### Phase 3 — Autonomous fanout (per non-tracer story)

For each story K-2..K-N in sprint-status order, spawn a fresh tmux session per story (current SKILL.md stage 5.2 mechanic preserved; v5 extracted spawn/poll/HALT-detect mechanics to the stdlib helper at `skills/bmad-auto/scripts/bmad-auto-helper.py` — SKILL.md prose now delegates to helper subcommands `spawn` / `monitor` / `halt-check`).

Per-story flow inside each tmux session:

**3a.** (Optional) `bmad-create-story` if the story isn't already detailed in `epics.md` / sprint-status. Auto-discovers from sprint-status.

**3b.** `bmad-testarch-atdd` → red scaffolds + ATDD checklist for this story

**3c.** `bmad-quick-dev` → makes red tests green + implements per spec

**3d.** `bmad-testarch-automate` OR `bmad-qa-generate-e2e-tests` → coverage expansion (non-blocking; user/config picks one)

**3e.** `bmad-code-review` → adversarial review per current bmad-code-review skill

Per-story HALT signals (v4 stored these in SKILL.md stage 5.2.9 prose; v5 extracted detection to the helper's `halt-check` subcommand at `skills/bmad-auto/scripts/bmad-auto-helper.py` — `final_state` enum is exactly `completed | halted | stalled | timeout`):

- `intent_gap` raised by quick-dev (v4 caught via capture-pane grep in prose; v5 caught by helper's `halt-check` against captured pane output)
- Loopback overflow (>5 iterations)
- VCS dirty / wrong branch
- Explicit HALT token
- (NEW) Tests not green after quick-dev exits (red tests still failing)

On HALT, current SKILL.md's stage 5.C.2 exit logic applies — `/bmad-auto` exits cleanly (v5: HALT classification is the helper's job via `halt-check` / `monitor` exit codes; the SKILL.md prose now wraps the helper's `final_state` verdict). **Sprint-status is the persistence layer.** Operator resolves the halt manually (e.g., resume quick-dev), then re-invokes `/bmad-auto --epics K` to continue the fanout from the next non-done story.

**Within-epic sequencing:** sequential by design (Alex's "sequential inside each [epic]"). Quick-dev's dependency assumptions presume serial execution. No parallel non-tracer stories.

---

### Phase 4 — End HITL (quality gates + digest + retrospective)

**4a.** `bmad-testarch-trace` → quality gate decision against the epic's diff
- Outputs: `traceability-matrix.md` + `e2e-trace-summary.json` + `gate-decision.json`
- Gate states: PASS / CONCERNS / FAIL / WAIVED

**4b.** `bmad-testarch-nfr` → NFR evidence audit (conditional on implementation evidence existing)
- Output: `nfr-assessment.md` + gate status PASS / CONCERNS / FAIL

**4c.** Codex review (current SKILL.md stage 7.1, preserved)
- Adversarial review against epic diff via different LLM (per Alex's principle)
- Output: `epic-K-codex-review.md`

**4d.** Deferred-work delta (current SKILL.md stage 7.2, preserved)
- Output: `epic-K-deferred-delta.md`

**4e.** Digest render (current SKILL.md stage 7.3, expanded)
- Includes: quality gate statuses, NFR audit summary, Codex review link, deferred-work counts, retrospective prompt
- Terminal print + saved to `_bmad-output/.run-state/run-digest-<runId>.md`
- One-screen budget honored (with HALT-context tail-trim per Phase 1 D5 deviation #1)

**4f.** Auto-spawn `bmad-retrospective` (heavy interactive, Alex's lessons-learned pattern)
- Party-mode multi-agent dialogue
- Outputs: `epic-K-retro-{date}.md` + sprint-status update (retrospective → `done`)
- Surfaces "significant discoveries" signal (Step 8) + critical-readiness status (Step 9)

**4g.** Conditional: `bmad-correct-course` auto-invocation
- If retrospective Step 8 emits significant discoveries OR Step 9 readiness FAILs, auto-prompt: *"Retrospective surfaced next-epic blockers. Run `/bmad-correct-course` now? [Y/n]"*
- If Y → invoke; if N → log and exit

**Combined gate logic (Phase 4):**
```
trace.gate_status: PASS | CONCERNS | FAIL | WAIVED
nfr.gate_status:   PASS | CONCERNS | FAIL  (only if implementation evidence exists)

IF trace == FAIL                                  → BLOCK, escalate
ELSE IF trace == CONCERNS AND nfr == FAIL         → BLOCK, escalate
ELSE IF (trace == PASS or CONCERNS) AND nfr ok    → proceed; operator decides at digest
ELSE IF trace == WAIVED                           → proceed with documented risk
```

---

## Headless mode (`--headless`)

Same phase structure as Express, but:

- **Phase 1:** all sub-phases run autonomously; SPIKES checklist auto-answers "yes" on all four (operator trusts upstream); per-epic spike triage defers everything dev-safe and HALTs on anything block-classified
- **Phase 2:** ATDD + quick-dev run with no operator engagement. Quick-dev's `intent_gap` escalation will pull operator in if it fires (Headless cannot suppress this)
- **Phase 3:** unchanged from Express — already autonomous
- **Phase 4:** Codex / deferred-delta / digest / trace / nfr run automatically. Retrospective is SKIPPED by default in Headless (auto-invoke would force operator in). `--with-retrospective` flag overrides.

**Headless is "best-effort autonomous" — not "guaranteed unattended."** Quick-dev's intent_gap, missing upstream artifacts, or quality-gate FAILs will surface to the operator post-hoc via digest or mid-flow if blocking.

Use cases:
- Re-runs after HALT-recovery patches
- Very simple epics where the tracer doesn't carry architectural weight
- Operators willing to walk away and review the digest later

---

## Guided mode (`--prep` / `--verify` / `--dev`)

Modal opt-in granularity — operator invokes each phase separately. Preserves current SKILL.md behavior:

- `--prep --epics K` — runs Phase 1 (1a-1g) and stops. Operator manually invokes `/bmad-quick-dev` on K-1, then `/bmad-auto --verify --epics K`.
- `--verify --epics K` — runs Phase 2c tracer-readiness gate only. Reports PASS/FAIL.
- `--dev --epics K` — runs Phase 3 + Phase 4. Skips Phase 1 (operator already did it) and Phase 2 (tracer already complete). Re-runs Phase 4 quality gates and retrospective.

Useful for operators who want phase-by-phase control.

---

## Input contract (per-epic)

By the time `/bmad-auto --epics K` runs in Express mode, these artifacts should exist (Phase 1 validates and offers to auto-invoke missing upstream):

| Artifact | Producer | Path pattern |
| --- | --- | --- |
| `brief.md` | `bmad-product-brief` | `{planning_artifacts}/briefs/brief-{project_name}-{date}/brief.md` |
| `SPEC.md` (preferred) OR `prd.md` | `bmad-spec` OR `bmad-prd` | `{spec_output_path}/SPEC-{slug}/SPEC.md` OR `{planning_artifacts}/prds/prd-{project_name}-{date}/prd.md` |
| `DESIGN.md` + `EXPERIENCE.md` | `bmad-ux` | `{ux_output_path}/ux-{project_name}-{date}/DESIGN.md` and `.../EXPERIENCE.md` |
| `architecture.md` | `bmad-create-architecture` | `{planning_artifacts}/architecture.md` (whole, not sharded) |
| `epics.md` | `bmad-create-epics-and-stories` | `{planning_artifacts}/epics.md` (single file, all epics + stories) |
| `sprint-status.yaml` | `bmad-sprint-planning` | `{implementation_artifacts}/sprint-status.yaml` |
| (Optional) `test-design-architecture.md` | `bmad-testarch-test-design` | system-level test plan |

**Non-negotiable: input layer is permissive.** When the upstream skill supports auto-invocation, `/bmad-auto` offers it inline rather than HALTing. The exceptions are skills that are heavily interactive (PRD, UX, architecture, create-epics-and-stories) — those must be precondition.

---

## Sub-skill invocation map

| Sub-skill | Where `/bmad-auto` invokes it | Interactivity | Headless support |
| --- | --- | --- | --- |
| `bmad-spec` | 1a (auto-invoke if missing) | Express (headless default) / Guided | ✓ JSON status block |
| `bmad-sprint-planning` | 1a (auto-invoke if missing) | Autonomous | (inherent) |
| `bmad-create-story` | 1a, 1g, 3a (auto-invoke for missing/thin stories) | Minimal — auto-discovers | (quasi-headless via auto-discover) |
| `bmad-check-implementation-readiness` | 1b (optional, Express prompts) | Step-based interactive | Not documented |
| `bmad-testarch-test-design` | 1c (optional system-level) | Interactive when ambiguous | Partial |
| `bmad-testarch-atdd` | 2a (tracer), 3b (per-story) | Interactive when ambiguous | Partial |
| `bmad-quick-dev` | 2b (tracer), 3c (per-story) | Heavy interactive on tracer; autonomous in tmux for non-tracer | (inherent on tracer; tmux-driven on non-tracer) |
| `bmad-testarch-automate` / `bmad-qa-generate-e2e-tests` | 3d (per-story coverage expansion) | Autonomous | (inherent) |
| `bmad-code-review` | 3e (per-story) | Autonomous | (inherent) |
| `bmad-testarch-trace` | 4a (quality gate) | Autonomous | (inherent) |
| `bmad-testarch-nfr` | 4b (NFR audit) | Autonomous | (inherent) |
| `bmad-retrospective` | 4f (auto-spawn) | Heavy interactive (party-mode) | Not documented |
| `bmad-correct-course` | 4g (conditional auto-prompt) | Interactive | Not documented |
| `bmad-tea` (Murat) | 1e SPIKES (operator-on-demand) | Interactive consultant | Not documented |

---

## SPIKES — where they live

The corrected picture (after multiple iterations):

| Stage | Skill | SPIKE behavior |
| --- | --- | --- |
| Upstream | brief, spec, UX, architecture, epics-and-stories | **Do not do spike work.** Surface assumptions / open_questions / `[ASSUMPTION]` tags. Route to research skills as suggestions only. |
| **`/bmad-auto` Phase 1** | **`/bmad-auto` itself** | **Per-epic spike triage lives HERE.** Extract upstream assumptions/open_questions touching K; SPIKES checklist (the 4-question + extended mechanic); per-epic spike/defer/block triage. |
| `/bmad-auto` Phase 2 | tracer-bullet via `bmad-quick-dev` | **The final SPIKE for the epic** — operator + quick-dev execute story K-1 with heavy HITL to resolve remaining unknowns. |
| `/bmad-auto` Phase 3 | per-story quick-dev (autonomous) | Residual spikes surface as quick-dev's `intent_gap` escalation. Operator pulled in only when needed. |

**No upstream BMAD skill orchestrates per-epic spike work.** That's `/bmad-auto`'s job, and it's why `/bmad-auto` exists as more than a thin orchestrator.

---

## Tests-first commitment

BMAD is tests-first (evidence). `bmad-dev-story` says explicitly: *"Write FAILING tests first... Confirm tests fail before implementation... Implement MINIMAL code to make tests pass."*

But `bmad-testarch-atdd` (the explicit red-phase scaffolding skill) is **not currently wired** into `bmad-story-automator` or `/bmad-auto`. Tests today live inside dev-story's internal RGR loop — not as separately auditable red scaffolds.

**`/bmad-auto`'s redesign fixes this.** Phase 2a + Phase 3b explicitly invoke `bmad-testarch-atdd` before `bmad-quick-dev`. Red tests become externally auditable artifacts (`atdd-checklist-{story_key}.md` + red test files), not implicit dev-story artifacts.

---

## Gaps vs. current SKILL.md (validation work scope-reset)

| # | Current SKILL.md | v2 intent |
| --- | --- | --- |
| 1 | Three explicit modes (--prep/--verify/--dev) | Three workflow modes (headless/express/guided); Express is default |
| 2 | Inspection-halt at tracer-readiness; operator manually invokes quick-dev | Express auto-invokes quick-dev in Phase 2; operator still engages heavily |
| 3 | HALTs if sprint-status missing | Auto-invokes `bmad-sprint-planning` (or `bmad-spec` / `bmad-create-story` etc. as appropriate) |
| 4 | Sprint-status is sole input contract | Accepts the full upstream contract: brief / PRD-or-SPEC / UX (DESIGN+EXPERIENCE) / architecture / epics.md / sprint-status |
| 5 | No just-in-time story breakdown | Auto-invokes `bmad-create-story` per Alex's "only first epic gets full breakdown" |
| 6 | No tests-first integration; no ATDD invocation | ATDD invoked per-story before quick-dev (Phase 2a + 3b) |
| 7 | No quality gates in Phase 4 | `bmad-testarch-trace` + `bmad-testarch-nfr` produce gate decisions feeding auto-merge |
| 8 | Retrospective is operator-discretion | Express auto-spawns `bmad-retrospective`; conditional `bmad-correct-course` if significant discoveries surface |
| 9 | No headless mode | Headless mode for re-runs / simple epics / walk-away operation |
| 10 | SPIKES checklist as prep-mode unique step | SPIKES checklist is part of Phase 1e in every mode (the per-epic hardening always runs in Express; auto-resolved to "yes" in Headless) |
| 11 | Ignores UX entirely | UX `DESIGN.md` + `EXPERIENCE.md` are first-class inputs; UX-DR precision checked in 1e |
| 12 | No bmad-spec awareness | SPEC.md is the preferred load-bearing input (replaces PRD per BMadCode direction); `companions: []` walk for adopted artifacts |

---

## Implications for validation work

| Phase 1 fixture | Status under v2 |
| --- | --- |
| D1 (HALT detection) | **VALID** — semantics unchanged. The new in-Phase-3 "tests not green" HALT signal extends the set, not replaces it. |
| D2 (deferred classifier) | **VALID** — semantics unchanged. |
| D3 (Codex flag probe) | **VALID** — Phase 4c still uses Codex; D8 work in old validation list still applies. |
| D4 (tmux send mechanic) | **VALID** — Phase 3 tmux-per-story mechanic unchanged. |
| D5 (digest dry-render) | **PARTIALLY VALID** — natural-exit / HALT-exit scenarios still apply; new digest sections (quality gate, NFR audit) need new scenarios. |

| Old gate | Status under v2 |
| --- | --- |
| G1 (scaffolding review) | Done |
| G2 (prep + verify) | **REPLACED** — new G2 covers Phase 1 (per-epic hardening + spike triage) end-to-end |
| G3 (dev mode) | **REPLACED** — new G3 covers Phase 2 (tracer-bullet via ATDD + quick-dev) and Phase 3 (autonomous fanout per-story with ATDD + quick-dev + automate + code-review) |
| G4 (Codex) | **EXPANDED** — new G4 covers all of Phase 4 (quality gates + Codex + deferred-delta + digest + retrospective) |
| G5 / G6 / G7 (review gates) | preserved structurally |

| Old D-task | Status under v2 |
| --- | --- |
| D6–D9 (heuristic patches) | **PARTIALLY OBSOLETE** — patch targets exist in v2 but stage numbers shift. Re-aim post-redesign. |
| D10–D12 (frontmatter stop-conditions) | **VALID** — applies to any workflow shape; especially useful for Headless mode tracer skipping. |

A new validation workstream replacing `bmad-auto-validate.md` will scope against the three modes and the per-story 5-step Phase 3 flow.

---

## Resolved questions (Q1-Q7 final state)

- **Q1 (tracer completion signal):** Tracer-readiness as single gate. In topology (A) direct-in-session, the gate runs as the first instruction of Phase 3 after quick-dev's flow returns control. Sprint-status check is INSIDE tracer-readiness (no separate trigger).
- **Q1c (intent_gap interception):** `/bmad-auto` stays out. Quick-dev's hardened intent_gap handling (revert + replan + 5-iteration limit + escalation) is the authoritative handler.
- **Q2 (SPIKES location):** SPIKES live INSIDE `/bmad-auto` Phase 1 (NOT delegated upstream). Per-epic hardening is `/bmad-auto`'s job. Multiple iterations got this wrong; v2 fixes it.
- **Q3 (modal `--prep` boundary):** Same as current SKILL.md — stops after Phase 1g tracer-readiness scaffolding. Operator manually invokes quick-dev, then `--verify`, then `--dev`.
- **Q4 (sub-skill auto-invocation contract):** Resolved during the sub-skill investigations (now consolidated into `SKILL.md`). Each sub-skill's interactivity profile mapped above in the invocation table.
- **Q5 (epics file format):** `{planning_artifacts}/epics.md` (single markdown file, all epics + stories, YAML frontmatter with `stepsCompleted[]` and `inputDocuments[]`). UX-DRs are first-class in epics.md.
- **Q6 (Headless tracer mechanics):** Tracer goes into the per-story fanout loop in Headless mode. ATDD + quick-dev both run autonomously; intent_gap still escalates to operator if it fires.
- **Q7 (retrospective auto-invocation):** Express auto-spawns `bmad-retrospective` at 4f. Headless skips (`--with-retrospective` overrides). Conditional `bmad-correct-course` at 4g if retrospective surfaces blockers.

---

## Open questions for the redesign

1. **Architecture spine / express mode timing:** `bmad-create-architecture` is interactive-only today. BMadCode's "architecture spine" + express mode is Discord-future. Does `/bmad-auto` design assume current architecture skill (precondition) or design for spine mode? Recommendation: design for current; forward-compat for spine.

2. **ATDD per-story always, or conditional?** Phase 3b invokes ATDD for every non-tracer story. Some stories might be trivial (e.g., docs-only) and ATDD overhead may not earn its place. Should there be a story-frontmatter opt-out (e.g., `atdd-skip: true`) or a stack-detection bypass?

3. **`bmad-correct-course` auto-invocation aggressiveness:** Should 4g auto-prompt every time retrospective surfaces ANY discovery, or only if Step 9 readiness FAILs?

4. **Spike-log persistence:** `epic-K-spike-log.md` would persist Phase 1f triage decisions across resumable runs. Should this be a new sidecar, or fold into an existing artifact?

5. **Resumability after Phase 1 spike-block:** if 1f marks an unknown as "block," operator exits, runs the spike skill, returns. Does `/bmad-auto` resume from 1f or restart 1a? Recommendation: read spike-log on entry, skip already-resolved items.

6. **Bmad-tea (Murat) consultation surface:** Phase 1e SPIKES checklist mentions Murat as an option for test strategy. Should the prompt explicitly offer it, or just have it as one option among the suggested skills?

---

## Next steps

1. ✅ Investigations complete (5 docs)
2. ✅ Design intent rewritten (this doc)
3. ⏳ Redesign [skills/bmad-auto/SKILL.md](../SKILL.md) against this intent. Preserve: HALT-detection mechanics (stage 5.2.9 — v5 extracted to helper `halt-check` / `monitor` at `skills/bmad-auto/scripts/bmad-auto-helper.py`; SKILL.md shrank 1517 → 1404 lines; tiered cadence 1-3→45s / 4-7→30s / 8+→20s now lives in helper `derive-cadence`), tmux send-sequence (stage 5.2.7), Codex invocation (stage 7.1, with [D3 corrections](../test-fixtures/codex-probe/findings.md)), digest composition (stage 7.3).
4. ⏳ Re-author [docs/auto-skills-design.md](auto-skills-design.md) to match.
5. ⏳ Create new validation workstream replacing bmad-auto-validate.md.
6. ⏳ Resume validation.
