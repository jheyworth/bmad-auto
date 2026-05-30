---
name: bmad-auto
license: MIT
description: Per-epic execution conductor. Drives a hardened epic from upstream artifacts (Brief / PRD-or-SPEC / UX / Architecture / epics.md / sprint-status.yaml) through per-epic hardening (hybrid parallel-scan + unified triage), tracer-bullet (heavy-HITL quick-dev on K-1), autonomous dev fanout (per-story ATDD + quick-dev + automate + code-review), and end-of-epic quality gates + digest + retrospective. Supports three workflow modes (Express default, Headless, Guided modal). Use when the user says 'run the auto sprint', 'execute prepared epic', 'auto-run epic K', or '/bmad-auto'.
---

# `bmad-auto`

`/bmad-auto` is the per-epic execution conductor implementing Alex Verhovsky's
pipeline. It takes a hardened epic and runs it through four phases, with HITL
concentrated at the beginning (per-epic hybrid hardening) and end (quality
gates + retrospective), and autonomous execution in the middle.

**Authoritative design source:**
[docs/bmad-auto-design-intent.md](docs/bmad-auto-design-intent.md) (v2).
**Sub-skill / upstream contracts:** the live sub-skill contract lives inline — the per-stage
prose below, [references/autonomous-mode-directives.md](references/autonomous-mode-directives.md)
(the quick-dev autonomous contract), and [docs/auto-skills-design.md](docs/auto-skills-design.md)
(non-negotiables). Note upstream `bmad-quick-dev` is a churning "New Preview
Workflow" with no native headless/express mode yet; bmad-auto forces autonomous
behavior via the directive injection in Stage 3.1. See
[docs/bmad-auto-agent-teams-decision.md](docs/bmad-auto-agent-teams-decision.md)
for the upstream-watch items (Agent Teams + quick-dev headless mode).

## What this skill does

`/bmad-auto --epics K` (Express mode, the default):

1. **Phase 1 — Per-epic hardening** (heavy HITL). Validate upstream artifacts.
   Auto-invoke missing upstream where supported. Extract residual unknowns
   for epic K from Spec / UX / architecture / epics.md. Run hybrid Phase 1
   hardening (parallel unknowns + edge-case scan, unified operator triage,
   optional `/good-ideas` escalation). Confirm tracer-bullet readiness.
2. **Phase 2 — Tracer-bullet** (heavy HITL). ATDD red scaffolds for story
   K-1, then `bmad-quick-dev` interactive in-session, then tracer-readiness
   gate.
3. **Phase 3 — Autonomous fanout** (per non-tracer story). Spawn a fresh
   tmux session per story. Per-story flow: optional `bmad-create-story` →
   `bmad-testarch-atdd` → `bmad-quick-dev` → coverage-expansion → code review.
4. **Phase 4 — End HITL.** Quality gates (`bmad-testarch-trace` +
   `bmad-testarch-nfr`) → Codex review → deferred-work delta → digest →
   auto-spawn `bmad-retrospective` → conditional `bmad-correct-course`.

Headless (`--headless`) collapses Phases 1/2 HITL into autonomous best-effort.
Guided (`--prep` / `--verify` / `--dev`) preserves the legacy modal workflow.

## When to use

User triggers:
- "run the auto sprint", "execute prepared epic", "auto-run epic N"
- `/bmad-auto --epics K` (any mode flag combination)
- Re-invocation after a HALT to resume from sprint-status state

Do NOT use when:
- Upstream pipeline isn't finished (brief / PRD-or-SPEC / UX / architecture /
  epics.md missing or in-progress). Phase 1a will detect and surface this.
- The epic in question is for parallel-front exploration that hasn't been
  story-broken-down yet — invoke `bmad-create-epics-and-stories` first.

---

## CLI surface

`/bmad-auto [MODE FLAGS] --epics <K>`

Mode flags (mutually exclusive within a group):

- **Workflow mode** (one of):
  - (no flag) — **Express** (default). Chained four-phase workflow.
  - `--headless` — **Headless**. Autonomous best-effort; minimal HITL.
  - `--prep` — **Guided prep**. Runs Phase 1 (1a–1f) and stops.
  - `--verify` — **Guided verify**. Runs Phase 2c tracer-readiness gate only.
  - `--dev` — **Guided dev**. Runs Phase 3 + Phase 4. Skips Phase 1 + 2.

- **Epic scope** (required for all modes):
  - `--epics K` — single epic identifier (e.g. `--epics 3`).

- **Modifiers** (optional, mode-dependent):
  - `--per-story-codex` — invoke Codex review per non-tracer story in
    addition to end-of-epic Codex (Phase 4c). Costs more; off by default.
  - `--with-retrospective` — Headless only. Auto-spawn `bmad-retrospective`
    at Phase 4f even in Headless mode. Off by default in Headless.
  - `--check-readiness` — Headless only. Run Phase 1b
    (`bmad-check-implementation-readiness`) even in Headless. Off by default
    in Headless.
  - `--skip-atdd` — Skip Phases 2a + 3b (ATDD red scaffolds). Use only for
    docs-only or trivial-refactor epics where ATDD overhead doesn't earn
    its place. **Off by default.** Tests-first remains the default posture.
  - `--no-codex` — explicit; overrides codex-available auto-detection.
    Equivalent to codex-unavailable for Phase 4c.

---

## Operator presentation conventions

Every operator-facing prompt in this skill uses one shared vocabulary, adopted
from the rest of bmad (`bmad-agent-*` menus, `bmad-retrospective` banners) so
bmad-auto reads like the skills around it. Render with plain text + emoji only
(no ANSI color): bmad-auto output is routinely captured to `.run-state` log
files and tmux panes, and must stay legible there.

- **Phase banner** — marks a phase or major-gate boundary *only* (not every
  prompt, or it stops meaning anything):

  ```
  ═══════════════════════════════════════════════════════════
  <emoji>  <TITLE> — Epic K · <subtitle>
  ═══════════════════════════════════════════════════════════
  ```

  Conductor emoji `🎛️`; phase emojis `🛡️` hardening · `🎯` tracer · `🚀`
  fanout · `🏁` end-HITL.
- **Status badge** — pair an emoji with bmad-auto's existing status words:
  `✅` PASS/done · `⚠️` CONCERNS/stall · `🚨` FAIL/significant-discovery.
- **Action menu** — when there are **≥3** discrete choices, render a numbered
  table with a `Code` (1–2 char) + `Description`, and close with, verbatim:
  **"Stop and wait for input. Accept a number, code, or fuzzy match."** Dispatch
  on a clear match; ask one short question only when two options are genuinely
  close — never a confirmation ritual.
- **Binary gate** — for a yes/no decision keep the existing `[Y/n]` / `[y/N]`
  line (capitalized letter is the default). Do **not** promote a binary into a
  menu — that is exactly the confirmation ritual the menu idiom forbids.

These conventions are presentation only. They never change a stage's decision
semantics, the persisted artifacts, or the headless/automation paths (which
emit no operator prompts at all).

---

## Stage 0 — Preflight (always runs first)

Run before any phase. Independent of mode.

1. **Probe `tmux`.** Run `command -v tmux`. If empty/non-zero exit:
   - Dev work (Phase 3 fanout) requires tmux. HALT with: *"`tmux` not
     found. Install via `brew install tmux` (macOS) or your platform's
     package manager. Phase 3 requires per-story tmux sessions."*
   - **Exception:** if mode is `--prep` only, allow proceeding without
     tmux (Phase 3 won't run in `--prep`).
2. **Probe Python 3.11+.** Run `command -v python3` and
   `python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'`.
   - If `python3` is missing OR the version check exits non-zero: HALT
     with: *"`python3 >= 3.11` not found. The helper at
     `scripts/bmad-auto-helper.py` (Phase 3 spawn / monitor / cadence
     derivation) requires Python 3.11+ (stdlib-only, no external
     deps). macOS Sonoma+ ships 3.11+ by default; verify with
     `python3 --version`."*
   - **Exception:** if mode is `--prep` only, allow proceeding (the
     helper is not invoked in Phase 1).
3. **Probe TEA module (BMad Test Architect).** `/bmad-auto` invokes
   three TEA skills: `bmad-testarch-atdd` (Stage 2.a, tracer ATDD
   scaffolds), `bmad-testarch-trace` (Stage 4.a, traceability +
   gate-decision), and `bmad-testarch-nfr` (Stage 4.b, NFR audit).
   Run:
   ```sh
   for s in bmad-testarch-atdd bmad-testarch-trace bmad-testarch-nfr; do
     test -f ".claude/skills/$s/SKILL.md" || echo "MISSING: $s"
   done
   ```
   - If any line prints `MISSING:`: HALT with *"TEA module not
     installed (missing: `<list>`). `/bmad-auto` requires the TEA
     module for Stage 2.a + Stage 4.a/4.b. Install via `/update-bmad`
     (re-clones with `--modules bmm,bmb,cis,tea,wds`) or directly:
     `npx bmad-method@next install --modules tea --tools claude-code`."*
   - **Exception:** if mode is `--prep` only, allow proceeding
     without TEA — Phase 1 does not invoke any testarch skill.
     Stage 2.a / 4.a / 4.b are out of scope for `--prep`.
   - Any-version policy: presence-only check; do not pin against
     `{project-root}/_bmad/tea/config.yaml` version. TEA evolves with the broader
     BMad release cadence; any installed version is accepted.
4. **Probe `codex`.** Run `command -v codex`.
   - If empty: set `codex_available=false`. Warn operator: *"`codex` not
     found. Phase 4c Codex review will be skipped. Install via `brew
     install codex-cli` to enable adversarial review."*
   - If present: set `codex_available=true`. Record version via
     `codex --version` to `_bmad-output/.run-state/codex-version.txt`
     (for D8 D3-corrected flag-set version pinning).
5. **Probe sprint-status.yaml.** Run
   `test -f _bmad-output/implementation-artifacts/sprint-status.yaml`.
   - If absent: NOTE — Phase 1a will auto-invoke `bmad-sprint-planning`
     if other upstream artifacts (epics.md) are present.
6. **Probe epics.md.** Run
   `test -f _bmad-output/planning-artifacts/epics.md`.
   - If absent: HALT with *"`epics.md` not found at
     `_bmad-output/planning-artifacts/epics.md`. Run
     `bmad-create-epics-and-stories` first. `/bmad-auto` cannot bootstrap
     from raw PRD/architecture (epics generation is heavily interactive)."*
7. **Probe epic K existence.** Read epics.md and confirm an epic section
   for K exists (search for `## Epic K` or `## Epic K:` headers, or
   sprint-status keys matching `^K-`).
   - If absent: HALT with *"Epic `K` not found in epics.md / sprint-status.
     Known epics: `<list>`. Pass a valid `--epics N`."*
8. **Probe optional architecture-spine / express mode (forward-compat).**
   Hedges against the BMadCode v6.8.0 roadmap "Next:" item — *"Architecture,
   story, dev, review skills get the same streamline"* (reinforcing the
   architecture-spine signal from BMadCode's Discord 2026-05-24). When the
   upstream `bmad-create-architecture` skill grows an express/spine/headless
   mode, Stage 1.a's downstream behavior changes from HALT-and-suggest to
   auto-invoke. This probe detects that transition.

   `bmad-create-architecture` is a Skill (not a CLI with `--help`
   introspection), so probe its source. Grep its SKILL.md and
   customize.toml for `express`, `spine`, or `headless` mode markers
   (case-insensitive):
   ```sh
   grep -l -i -E '\b(express|spine|headless)\b' \
     .claude/skills/bmad-create-architecture/SKILL.md \
     .claude/skills/bmad-create-architecture/customize.toml \
     2>/dev/null
   ```
   If any match: set `architecture_has_express=true`. Otherwise: set
   `architecture_has_express=false`. Store the value in
   `_bmad-output/.run-state/architecture-mode.txt`. Phase 1a consumes
   this signal (see Stage 1.a's `architecture.md` row). Defaults false
   until upstream ships the architecture-spine streamline; cross-ref
   [`docs/auto-skills-design.md`](docs/auto-skills-design.md)'s
   "Architecture artifact contract" section for the broader narrative.
9. **Generate `<runId>`.** UTC timestamp via
   `date -u +%Y%m%dT%H%M%SZ`. Record in orchestrator-session memory; do
   not regenerate per story. Unique-per-run is non-negotiable.
10. **Initialize run-state dir.** `mkdir -p _bmad-output/.run-state`.

---

## Mode dispatch

After Preflight:

- `--prep` → Phase 1 (1a–1f) only, then exit with handoff message.
- `--verify` → Phase 2c only, then exit with PASS/FAIL message.
- `--dev` → Phase 3 + Phase 4. Skip Phases 1 + 2 (operator already did them).
- `--headless` → Phase 1 collapsed (autonomous, no HITL prompts); **Phase 2
  collapsed entirely — tracer K-1 joins Phase 3's per-story fanout loop as
  story #1**; Phase 3 runs as usual (already autonomous); Phase 4 quality
  gates + Codex + digest run; retrospective skipped (operator review
  post-hoc unless `--with-retrospective`).
- (default Express) → all four phases with HITL at Phase 1 + 2 + 4.

**Mode selection (only when no workflow-mode flag is given).** If the
invocation carries an explicit workflow-mode flag (`--headless` /
`--prep` / `--verify` / `--dev`), or the operator's trigger phrasing
clearly names one ("headless run", "just prep epic K"), dispatch it
directly — no menu. Otherwise, in an interactive session, render the
mode menu (per *Operator presentation conventions*) rather than
silently assuming Express:

```
═══════════════════════════════════════════════════════════
🎛️  BMAD-AUTO — Epic K · select run mode
═══════════════════════════════════════════════════════════
 Code  Mode      HITL     Runs
 EX    Express   heavy    P1 triage · P2 tracer in-session · P3 fanout · P4 gates+retro   (default)
 HL    Headless  minimal  autonomous P1 scan · tracer joins P3 · P4 gates+Codex · no retro
 PR    --prep    heavy    Phase 1 only, then hand off to you
 VF    --verify  light    tracer-readiness gate only
 DV    --dev     auto     Phase 3 + 4 (assumes P1–2 already done)

Stop and wait for input. Accept a number, code (EX/HL/PR/VF/DV), or mode
name. Enter selects Express.
```

`Enter` (empty input) selects **Express** — this preserves the
documented "(no flag) → Express" default, so a non-interactive or
scripted bare `/bmad-auto --epics K` still proceeds as Express without
blocking. The menu only ever surfaces an ambiguous *interactive*
invocation; it never gates automation.

**Express signposting (before Phase 1):**

Print to operator (verbatim, all modes except `--prep`):

> Express mode will:
> 1. Validate upstream artifacts for epic `K` and offer to auto-invoke
>    missing upstream where supported.
> 2. Walk you through per-epic hybrid hardening (Phase 1).
> 3. Auto-invoke `/bmad-quick-dev` for the tracer story K-1 in this
>    session (Phase 2). You'll interact heavily with quick-dev.
> 4. Spawn per-story tmux sessions for stories K-2..K-N running
>    autonomously (Phase 3). Each spawned session uses
>    `--dangerously-skip-permissions`.
> 5. Run quality gates + Codex review + digest + retrospective (Phase 4).
>
> Proceed? `[y/N]`

Default `N`. Only `y`/`yes` advances. This is the **single** consent
gate for the `--dangerously-skip-permissions` posture used in Phase 3.

**Headless signposting** is identical but with one extra line:
*"Headless mode is best-effort autonomous. Quick-dev intent_gap, missing
upstream, or quality-gate FAILs will surface to you post-hoc."*

---

## Phase 1 — Per-epic hardening (Express + Guided `--prep`)

Heavy HITL. The operator drives; `/bmad-auto` structures.

### Stage 1.a — Input validation + auto-invocation

For each artifact in the input contract, check presence and offer to fix
missing items inline:

| Artifact | Path | If missing |
| --- | --- | --- |
| `brief.md` | `_bmad-output/planning-artifacts/briefs/*/brief.md` (glob) | Surface as gap; offer to invoke `bmad-product-brief` |
| `SPEC.md` (preferred) OR `prd.md` | `_bmad-output/specs/spec-*/SPEC.md` (new flat convention per bmad-spec customize.toml; PR #2417 in BMAD-METHOD) OR `_bmad-output/planning-artifacts/prds/*/prd.md` (PRD still uses legacy planning-artifacts path) | If PRD exists but no SPEC: offer auto-invoke `bmad-spec` (has headless mode, JSON status block). If neither: HALT, recommend `bmad-prd` or `bmad-spec` |
| `DESIGN.md` + `EXPERIENCE.md` | `_bmad-output/planning-artifacts/ux-designs/*/DESIGN.md` and `.../EXPERIENCE.md` | **Conditional on SPEC's UX-surface declaration.** If SPEC declares no UX surface (frontmatter `ux_surface: none`, OR a non-goal explicitly stating "no UX" / "no UI" / "no user-facing surface", OR a CLI/library/service scope with zero UI affordances), the gate is vacuously satisfied — skip silently. Otherwise both required: if missing, HALT and recommend `bmad-ux` (interactive, two-spine artifact). Mirrors Stage 4.b's "Skip if no NFR-touching code" conditional |
| `architecture.md` | `_bmad-output/planning-artifacts/architecture.md` (whole, not sharded) | Required. Check frontmatter `status: 'complete'` AND `stepsCompleted: [1,2,3,4,5,6,7,8]`. If missing: HALT (architecture is interactive-only today; no headless/express mode in the upstream `bmad-create-architecture` source as of last check). **Forward-compat (architecture-spine streamline):** if `architecture_has_express=true` from Preflight 6, the upstream skill has shipped an express/spine mode — offer auto-invoke instead of HALT |
| `epics.md` | `_bmad-output/planning-artifacts/epics.md` | Already validated in Preflight 4 |
| `sprint-status.yaml` | `_bmad-output/implementation-artifacts/sprint-status.yaml` | If missing AND epics.md present: auto-invoke `bmad-sprint-planning` (fully autonomous, scans all epics) |
| Epic K's stories detailed in sprint-status | `K-N-<slug>` keys present | If K's stories not broken down (per Alex's "only first epic gets full detail"): auto-invoke `bmad-create-story` for K. Auto-discovers from sprint-status |
| Per-story spec files for epic K | `_bmad-output/implementation-artifacts/K-N-*.md` (one per non-tracer story key in sprint-status) | If any are missing: auto-invoke `bmad-create-story` for each missing key. `bmad-create-story` is an autonomous sub-skill (per the auto-invocation pattern below); skip the `[Y/n]` prompt in Express mode if operator has already passed the Phase-level ratification gate. **HITL note (Express):** if multiple files are missing, batch the invocations and surface a summary to the operator after the last one completes. **Headless:** auto-invoke without prompting. **Rationale:** Stage 2.a (tracer ATDD) requires the K-1 file path; this check guarantees the file exists before Phase 2 launches. Stage 3 (autonomous fanout) does not require pre-existing files — see Stage 3.1 "Story-file handling contract" delegation note. |

**Auto-invocation pattern (general principle, applies anywhere
`/bmad-auto` auto-invokes a sub-skill — Stages 1.a, 1.f, and any
future addition):**

- **Interactive sub-skills** (e.g. `bmad-ux`, `bmad-prd`,
  `bmad-create-architecture`, `bmad-create-epics-and-stories`): prompt
  operator `Run /bmad-<skill> now to fix? [Y/n]` with `n` as default.
  The prompt has decision-value — the operator may decline and run it
  manually later. On `y`, invoke and resume this stage on completion.
  On `n`, HALT with a list of remaining gaps.
- **Autonomous sub-skills** (skills whose own SKILL.md declares
  "ZERO USER INTERVENTION" or an equivalent headless posture — e.g.
  `bmad-spec` headless mode, `bmad-sprint-planning`,
  `bmad-create-story`): when invoked **inside an already-consented
  phase** (operator has already passed a Phase-level ratification or
  the Express signposting `[y/N]` gate), skip the `[Y/n]` prompt and
  invoke directly. The prompt would have no decision-value: the
  sub-skill has nothing for the operator to engage with, and consent
  was already captured upstream. Log the invocation to
  orchestrator-session memory so it shows up in the digest.
- **Heuristic for "is this skill autonomous?"** — check the sub-skill's
  own SKILL.md description. Phrases like "ZERO USER INTERVENTION",
  "fully autonomous", "headless mode", or "no operator interaction"
  classify it as autonomous. When in doubt, treat as interactive
  (the `[Y/n]` prompt is cheap; skipping it when it shouldn't be is
  not).

**Batched gaps checklist (Express, ≥2 interactive offers).** When the
table leaves **two or more** *offer-to-auto-invoke interactive* gaps
(e.g. `bmad-product-brief`, `bmad-ux`, `bmad-create-architecture` where
an express/spine mode exists), present them as one checklist menu
instead of sequential `[Y/n]` prompts (per *Operator presentation
conventions*). A single interactive gap keeps the inline `[Y/n]` from
the auto-invocation pattern above — don't promote one offer into a menu:

```
═══════════════════════════════════════════════════════════
🧩  UPSTREAM GAPS — Epic K  (<G> to resolve)
═══════════════════════════════════════════════════════════
 [ ] 1  UX spec                → bmad-ux                  (interactive)
 [ ] 2  Architecture           → bmad-create-architecture (interactive)
 [x] 3  Story specs (K-2..K-N) → bmad-create-story        (autonomous — runs regardless)

Interactive gaps start unchecked; autonomous skills are pre-checked and run
regardless (shown for transparency). Toggle interactive numbers to run now
(e.g. "1 2"), then "go".

Stop and wait for input. Accept numbers to toggle, "go", or a fuzzy match.
```

On `go`: invoke each checked interactive gap (then the autonomous ones)
and resume this stage. Any interactive gap left **unchecked** is a
decline — fall through to the pattern's HALT-with-remaining-gaps once
the checked items finish. Hard-HALT preconditions (no SPEC *and* no
PRD; required `architecture.md` missing with no express mode; required
UX missing) are **not** checklist rows — they HALT before this menu per
the table's "If missing" column. This complements the existing story-file
batching note in the table (autonomous, summarized after the last one).

**In Headless mode:** auto-invoke autonomous skills without prompting;
HALT on missing interactive-only skills (PRD, UX, architecture,
create-epics-and-stories) with a clear precondition message.

### Stage 1.b — Optional Phase 3→4 readiness gate

In Express mode, prompt:

> Run `bmad-check-implementation-readiness` for Phase 3→4 readiness
> validation? `[Y/n]` (recommended)

On `y`: invoke `bmad-check-implementation-readiness`. Read the report:

- READY → continue to 1c
- NEEDS WORK → surface report; prompt *"Proceed at documented risk?
  `[y/N]`"*. Default `N`.
- NOT READY → HALT. Surface specific failures (missing FRs, coverage
  gaps, etc.) and recommend remediation.

In Headless mode: skip unless `--check-readiness` was passed.

### Stage 1.c — (Optional) System-level test plan

Check for `_bmad-output/planning-artifacts/test-design-architecture.md`.
If absent, prompt:

> Run `bmad-testarch-test-design` (system-level) to produce a test plan
> + risk assessment + NFR thresholds? `[Y/n]`

Non-blocking. Operator can defer.

### Stage 1.d — Unknown extraction for epic K

Programmatic; low HITL. Surface a consolidated unknown-report to operator.

1. **Walk SPEC's `companions: []`** (from SPEC.md frontmatter, if SPEC
   exists). For each path, read and identify any unknowns touching K's
   CAP-N's.
2. **Extract `[ASSUMPTION]` tags** via
   `grep -r '\[ASSUMPTION\]' <brief.md, DESIGN.md, EXPERIENCE.md>` and
   filter for ones touching epic K's scope.
3. **Extract SPEC's `assumptions[]` and `open_questions[]`** (if SPEC
   exists). Cross-reference K's CAP-N's via Spec's capability→epic
   mapping (or by manual scan if no formal mapping exists).
4. **Extract epics.md Step-4 validation gaps** for K. Look for any
   coverage warnings or missing-AC notes in epics.md's epic-K section.
5. **Extract architecture Gap Analysis items** affecting K. Read
   `architecture.md` Section 7 (Architecture Validation Results → Gap
   Analysis); surface Critical/Important items mentioning K's scope.
   Note: architecture has no structured `open_questions[]` array — read
   as prose.

Present consolidated report to operator (one screen if possible):

```
Epic K — residual unknowns:

[1] [ASSUMPTION] (brief.md): "<text>"
[2] open_question (SPEC.md, touching CAP-3): "<text>"
[3] gap (epics.md Step-4): "<text>"
[4] architecture gap (Critical): "<text>"
...
```

### Stage 1.e — Hybrid Phase 1 hardening

Single-stage hardening that combines an external-unknowns scan
(SPIKES method) with an internal-story-quality scan
(edge-case-hunter method). Both run in parallel as Task subagents;
the orchestrator collates a unified triage menu and the operator
decides each finding's disposition. Optional `/good-ideas`
escalation deepens analysis for any finding the operator wants to
attack harder before triaging.

This stage replaces the prior two-stage SPIKES + spike-triage flow.
External and internal hardening were always the same goal (harden
the epic before Phase 2 launch) on different attack surfaces;
combining them closes the internal-quality gap and removes the need
for any mid-Phase-3 pause.

**Step 1 — Scan + collate (workflow).** Invoke the bundled
`phase1e-scan` workflow — do **not** hand-spawn the two Task
subagents. The workflow runs both hunters in `parallel()`, each
forced to emit schema-valid findings JSON (the contract below) at the
tool layer, then collates deterministically in JS (dedupe +
cross-link) and persists the findings file from a writer step inside
the workflow. This keeps both ~110-line hunter prompts and the two
raw JSON blobs off the orchestrator's main context, and removes the
lossy "orchestrator hand-transcribes the JSON" failure mode.

Invoke it with the `Workflow` tool (the skill instructing this call
is the explicit opt-in; this uses the Workflow/Agent-SDK path, never
`claude -p`). First capture a timestamp (`date -u
+%Y-%m-%dT%H:%M:%SZ`) to pass as `now`, then:

```
Workflow({
  scriptPath: "skills/bmad-auto/workflows/phase1e-scan.workflow.js",
  args: {
    epic_id: "K",
    story_paths: ["<abs path to each K-N story file>"],
    architecture_path: "<abs path to architecture.md, if present>",
    epics_path: "<abs path to epics.md, optional>",
    impl_paths: ["<abs paths to code the hunters should run/grep, optional>"],
    repo_root: "<abs repo root, for running the CLI / grep>",
    out_path: "<abs path>/_bmad-output/.run-state/epic-K-phase1-findings.json",
    now: "<UTC ISO-8601 from date -u>"
    // verify: omit (default false) — see "Optional verification" below
  }
})
```

The two hunters get **execute-access** (read + run, no writes): the
unknowns-hunter runs the real artifacts and greps `.github/`; the
edge-case-hunter confirms each trigger against real code before
reporting it. Granting execute-access is the single biggest
finding-quality lever (a blind read-only unknowns scan returns ~0).
The embedded hunter prompts mirror
[references/unknowns-hunter-prompt.md](references/unknowns-hunter-prompt.md)
and
[references/edge-case-hunter-prompt.md](references/edge-case-hunter-prompt.md),
which remain the human-readable method spec.

The workflow returns `{ out_path, scan_summary, persisted,
persist_matches_collate, collated, ... }`. Confirm
`persist_matches_collate === true` (the writer wrote exactly the
JS-collated findings); if false, re-run before triaging.

**Findings JSON schema (contract between scan and triage).** The
workflow enforces the per-finding shape at the tool layer (the hunters
cannot return malformed findings — the model retries on mismatch), so
this is the guaranteed shape of each entry in the persisted file:

```json
{
  "epic_id": "K",
  "scan_at": "<UTC ISO 8601>",
  "findings": [
    {
      "id": "<source>-<n>",
      "source": "unknowns | edge-case",
      "category": "<spike-category or edge-category>",
      "severity": "FAIL | CONCERNS | INFO",
      "story_id": "<K-N or null for epic-scope>",
      "description": "<one-paragraph>",
      "cross_layer_flags": ["<finding-id>", ...]
    }
  ]
}
```

Severity calibration: `FAIL` blocks Phase 2 entry until resolved or
explicitly waived; `CONCERNS` requires an operator decision but does
not block; `INFO` is nice-to-know.

**Step 2 — Collate + persist (inside the workflow).** The workflow
already did this: it merged both hunters' findings, collapsed
byte-identical descriptions, cross-linked findings that share a
mechanism token or `cli.py:NN` code reference (populating
`cross_layer_flags`), built `scan_summary` (incl. `unknowns_notes`),
and persisted the result to
`_bmad-output/.run-state/epic-K-phase1-findings.json`. The persisted
file carries the scan+collate contract only (`epic_id`, `scan_at`,
`collated_at`, `scan_summary`, `findings[]`); the `triage_outcome` /
`triage_note` per-finding fields and the top-level `triage_summary`
are appended later by Step 4. The orchestrator does **not** re-write
the file here — it reads the persisted JSON (or the workflow's
returned `collated`) to drive triage.

**Step 3 — Present the triage menu.** Open with a hardening banner
and the severity tally as badges (per *Operator presentation
conventions*), then one table row per finding:

```
═══════════════════════════════════════════════════════════
🛡️  PHASE 1 HARDENING — Epic K · Triage  (<N> findings)
═══════════════════════════════════════════════════════════
   🚨 FAIL <f>   ·   ⚠️ CONCERNS <c>   ·   INFO <i>        verify: <on|off>

  #   sev       source     category   story   finding                  xrefs
  1   FAIL      unknowns   Packages   —       <one-line description>   edge-case-3
  2   CONCERNS  edge-case  branch     K-2     <one-line description>   —
  …
```

**Step 4 — Triage each finding via the action menu.** Below the
table, render the per-finding action menu and wait. The three
outcomes and their recorded `triage_outcome` are unchanged — the menu
is just the surface over them:

```
Per-finding — enter "<#> <code>", e.g. "2 D":
  R  Resolve now      work the concern in-session (amend story/ACs, install a
                      package, run a spike skill); record triage_outcome "resolved" + note
  D  Defer to digest  log it; epic proceeds; it surfaces in the Stage 4.e digest;
                      record triage_outcome "deferred"
  S  Split off        finding belongs outside epic K; move/out-of-scope the story;
                      record triage_outcome "split-off" + destination
  G  Good-ideas       escalate this finding to /good-ideas (Step 5) before deciding

Batch:  A D  (all → defer)   ·   A R  (all → resolve)   ·   F R  (all FAIL → resolve)
View:   show <#>   full description + cross-refs
Then:   done   to gate Phase 2 (Step 6)

Stop and wait for input. Accept "<#> <code>", a batch op, "show <#>", "done",
or a fuzzy match.
```

Every finding must end with a `triage_outcome` (resolved / deferred /
split-off) before `done`. Re-rendering the table after each choice, or
showing a running `<n>/<N> triaged` line, is fine — whatever keeps the
remaining set clear. The `F R` batch only sets the *intent* to resolve
FAILs; Step 6 still confirms each was actually resolved.

**Step 5 — `/good-ideas` escalation (the `G` code).** When the
operator picks `G` for a finding, invoke `/good-ideas` mode to deepen
the adversarial attack before deciding its triage outcome. The `/good-ideas`
skill runs operator-collaborative (Depth Trigger Guardrail requires
human back-and-forth), so it runs inline in the orchestrator session
— not as a subagent. Hardened thoughts from `/good-ideas` append to
that skill's persistent log per its protocol. On return, operator
picks resolve / defer / split-off.

**Step 6 — Gate Phase 2.** Stage 1.e completes only when every
finding has a `triage_outcome`. If any `severity: FAIL` finding has
`triage_outcome: "resolved"` but the underlying issue was not
actually resolved (operator says so on a final confirmation prompt),
Stage 1.e HALTs and Phase 2 launch is blocked. Re-invoke
`/bmad-auto --epics K` to resume; the findings JSON persists.

Append per-finding `triage_outcome` (and any resolution note) into
`_bmad-output/.run-state/epic-K-phase1-findings.json`. The same file
is the source of truth on re-entry: already-triaged findings are
skipped on resume.

**Optional verification (OFF by default).** The default Stage 1.e
path is scan → collate → triage; there is **no** automatic
verify/filter stage. The workflow exposes an opt-in `verify: true`
arg, but it is deliberately constrained so it can never do the
operator's job:

- **FAIL-gated.** Only `severity: FAIL` findings are checked; CONCERNS
  and INFO are never touched.
- **Factual-only calibration.** A verifier may flag a finding only if
  it is *factually wrong* (the described trigger does not actually
  occur, the code is misdescribed, or a cited state does not exist) —
  **never** on scope, theory ("won't happen for this CLI"), or
  severity. Those are triage judgments.
- **Annotate, never drop.** A verdict attaches a `verify` flag to the
  finding for the operator; it **never** removes a finding or changes
  the triage set.

Rationale (spike evidence): a naive "adversarial, default-refute,
launch-blocker bar" verifier refuted 12/12 *factually real* findings
(it did operator triage at a block-or-not bar and discarded every
CONCERNS/INFO). The same findings under a factual-only bar were kept
14/14, removing zero — i.e. the scan is already high-quality and
per-finding verification is low-ROI. So verification is reserved as an
opt-in FAIL-severity sanity flag, not a default keep/drop filter.

**Headless mode.** Skip operator triage. Invoke the same
`phase1e-scan` workflow (scan + collate + persist), then auto-mark
every finding `triage_outcome: "deferred"` by appending the triage
fields to the persisted JSON. All findings surface in the Stage 4.e
end-HITL digest. Exception: any `severity: FAIL` finding HALTs
Headless mode for operator triage — Headless cannot silently launch
Phase 2 over a FAIL.

### Stage 1.f — Tracer-bullet readiness

1. Confirm story K-1 exists in `epics.md` and `sprint-status.yaml`.
2. Read the K-1 story file (`_bmad-output/implementation-artifacts/K-1-*.md`).
3. Check tracer story has functional ACs (not just `<TODO>` placeholders).
4. If missing or thin: auto-invoke `bmad-create-story` for K-1
   (auto-discovers from sprint-status). `bmad-create-story` is
   autonomous-by-design ("ZERO USER INTERVENTION" per its own SKILL.md)
   — per the Stage 1.a auto-invocation pattern, skip the `[Y/n]` prompt
   and invoke directly; Phase 1 ratification already covered consent.
   Operator engagement happens only if sprint-status is ambiguous
   (the sub-skill will surface its own prompts in that case).
5. Phase 1 complete.

**Exit handoff (Guided `--prep` mode only):** print verbatim:

> Phase 1 complete. Tracer story scaffolded at `<path>`.
>
> Either continue with `/bmad-auto --epics K` (Express resumes from
> Phase 2), or run modal:
>   `/bmad-quick-dev` against K-1
>   `/bmad-auto --verify --epics K` to confirm tracer-readiness
>   `/bmad-auto --dev --epics K` to fanout

In Express + Headless: proceed directly to Phase 2.

---

## Phase 2 — Tracer-bullet (Express only)

The final SPIKE for epic K. Resolves remaining unknowns via story K-1
execution.

**This phase runs in Express mode only.** In Headless mode, Phase 2
collapses entirely — story K-1 joins Phase 3's per-story fanout loop
as story #1 and runs autonomously in a tmux session like other
non-tracer stories. See "Headless mode" section below. In Guided
mode, the operator runs `--prep` → manual `/bmad-quick-dev` → `--verify`
→ `--dev`, so the Phase 2 stages below correspond to the operator's
manual middle step.

**Topology: direct in-session.** `/bmad-auto`'s instructions invoke
`bmad-testarch-atdd` then `bmad-quick-dev` in this Claude Code session.
The operator interacts with quick-dev's prompts directly.

### Stage 2.a — ATDD red-phase scaffolds

Skip if `--skip-atdd` was passed.

1. Invoke `bmad-testarch-atdd` against story K-1.
2. Pass story file path as input; ATDD auto-detects stack from project
   manifests.
3. Wait for completion. Verify outputs:
   - **ATDD checklist** at the skill's canonical path:
     `_bmad-output/test-artifacts/atdd-checklist-<story_key>.md`,
     where `<story_key>` is the story filename's `.md`-less stem
     (e.g. `99-1-validation-sandbox-skeleton`), per
     `bmad-testarch-atdd`'s `outputFile: '{test_artifacts}/atdd-checklist-{story_key}.md'`
     frontmatter and `{project-root}/_bmad/tea/config.yaml`'s
     `test_artifacts: "{project-root}/_bmad-output/test-artifacts"`. Do
     not pass an override path — the ATDD skill ignores caller overrides
     and writes to its config-resolved location.
   - Generated red test files (E2E/API/Component skeletons)
   - Fixture stubs and helper signatures
4. **Discover the exact checklist path** with the deterministic glob
   `_bmad-output/test-artifacts/atdd-checklist-<K>-1-*.md`. The
   `<K>-1-` prefix uniquely identifies the tracer story's checklist
   even when the trailing slug is unknown to the orchestrator. If zero
   matches: HALT — ATDD did not produce its checklist. If multiple
   matches: pick the most recently written file (newest `mtime`) and
   log the ambiguity.
5. **Validate red tests are red.** Run the test runner. Tests must fail.
   If any pass before implementation, HALT — ATDD scaffolding has a
   defect (likely a test that doesn't actually exercise the AC).
6. Note the resolved ATDD checklist path to orchestrator-session memory
   (so Stage 2.b's quick-dev invocation can pass it as a reference).

### Stage 2.b — Tracer implementation via quick-dev

1. Invoke `bmad-quick-dev` against story K-1.
2. Quick-dev reads the K-1 story file + ATDD checklist at the path
   resolved in Stage 2.a step 4 (the `_bmad-output/test-artifacts/`
   canonical location, not `implementation-artifacts/`).
3. **Operator interacts heavily.** This is the heavy-HITL moment per
   Alex's pipeline. Operator and quick-dev together:
   - Make red tests green
   - Produce micro-PRD and micro-architecture (Format A) — or rely on
     the whole-project `architecture.md` (Format A-equivalent, the
     default for single-epic projects)
   - Surface and resolve architectural decisions for the rest of
     epic K
4. Quick-dev's internal HALT machinery handles `intent_gap`:
   - Code reverts; operator clarifies intent; quick-dev replans (step-02)
   - Iteration limit: max 5 (per quick-dev's `specLoopIteration`)
   - On 5th iteration without resolution: quick-dev itself HALTs and
     escalates
5. **`/bmad-auto` does NOT intercept** intent_gap signals. Quick-dev's
   flow is the authoritative handler.
6. When quick-dev's flow ends (story marked done, or operator aborts):
   control returns to `/bmad-auto`. Proceed to 2c.

### Stage 2.c — Tracer-readiness gate

Single gate. Run the logic in `references/tracer-readiness-check.md`.
The reference defines a two-way format precedence (Format A → Format
A-equivalent). Format A-equivalent is the **default** path under
unmodified BMAD toolchains for single-epic-per-invocation projects
(see Producer note below).

Checks (per the reference's format-detection precedence):
1. Sprint-status: K-1 story key has value `done` (both formats).
2. **Format A** (when both
   `_bmad-output/implementation-artifacts/epic-K-micro-prd.md` and
   `_bmad-output/implementation-artifacts/epic-K-micro-architecture.md`
   exist): both files with all required sections non-empty.
3. **Format A-equivalent (whole-project short-circuit; default fall-
   through)** — `_bmad-output/planning-artifacts/architecture.md` with
   frontmatter `status: 'complete'` AND `stepsCompleted: [1..8]`, plus
   one of `_bmad-output/specs/spec-*/SPEC.md` or
   `_bmad-output/planning-artifacts/prds/*/prd.md`. No section-level
   header checks (whole-project artifacts use canonical BMAD section
   names, not micro-doc names).
4. Red tests from Stage 2a now pass (if `--skip-atdd` was not used).
   Run the test runner against K-1's tests.

**Producer note (Format A vs A-equivalent):** no BMAD skill currently
produces the per-epic `epic-K-micro-prd.md` / `epic-K-micro-architecture.md`
pair automatically. If Stage 2.b's quick-dev or a subsequent operator
hand-edit has authored them, the gate runs as Format A. Otherwise it
falls through to Format A-equivalent against the whole-project
architecture + SPEC, which is the realistic default. Multi-epic projects
that need genuine per-epic distillation should author the micro-docs
explicitly during Phase 2.b (operator-driven). The architecture-spine
streamline signaled in BMAD-METHOD v6.8.0's roadmap may evolve this
contract further; cross-reference [`docs/auto-skills-design.md`](docs/auto-skills-design.md)'s
"Architecture artifact contract" section for the broader narrative.

On PASS → proceed to Phase 3.

On FAIL → HALT with the specific failure message(s) per
`references/tracer-readiness-check.md` § "Failure modes" + this
remediation directive (verbatim):

> Tracer-readiness failed. Fix the issues above and either:
> - Re-invoke `/bmad-auto --epics K` (Express will retry from Phase 2),
>   OR
> - Manually run `/bmad-quick-dev` to resume work on K-1, then
>   `/bmad-auto --verify --epics K` to re-check, then
>   `/bmad-auto --dev --epics K` to fanout.

In Guided `--verify` mode: exit cleanly after gate evaluation (PASS or
FAIL). Do not proceed to Phase 3.

---

## Phase 3 — Autonomous fanout (Express + Headless + Guided `--dev`)

For each non-tracer story K-2..K-N in sprint-status order, spawn a fresh
tmux session and execute the per-story flow. Sequential within the epic
(per Alex's "sequential inside each [epic]").

### Stage 3 setup (runs once before per-story loop)

1. **Capture `epic-K-start.sha`.** Run `git rev-parse HEAD`.
   - On success: record SHA to `_bmad-output/.run-state/epic-K-start.sha`
     (for Phase 4c Codex range). Continue.
   - On failure (not a git repo): fall back to path-based marker. Read
     touched paths from `epic-K-micro-architecture.md` (Format A) or
     from the whole-project `_bmad-output/planning-artifacts/architecture.md`
     (Format A-equivalent) and record to
     `_bmad-output/.run-state/epic-K-start.paths`. Warn operator:
     *"Not a git repo. Codex range will be path-based; coverage may
     degrade."*
2. **Capture `deferred-work-start.snapshot`.** Run:
   `test -f _bmad-output/implementation-artifacts/deferred-work.md && wc -l _bmad-output/implementation-artifacts/deferred-work.md && shasum _bmad-output/implementation-artifacts/deferred-work.md || echo MISSING`.
   - If exists: record `lines:<N> sha:<hexdigest>` to
     `_bmad-output/.run-state/deferred-work-start.snapshot`.
   - If MISSING: record `lines:0 sha:none`.
3. **Identify story list.** Read sprint-status.yaml. Enumerate keys
   matching `^K-` (excluding `K-retrospective`). Filter to status ∈
   {`backlog`, `ready-for-dev`, `in-progress`}.
   - **Express + Guided `--dev` modes:** also exclude `K-1` (the
     tracer). Phase 2 already handled it (Express) or operator already
     ran it manually before invoking `--dev` (Guided).
   - **Headless mode:** include `K-1` as story #1 in the loop. This is
     where Phase 2 collapses — the tracer runs autonomously in a tmux
     session like other stories. If quick-dev raises `intent_gap` for
     K-1 in Headless, the standard HALT-detection in Stage 3.4 catches
     it and the run exits cleanly via Stage 3.C.2. The operator
     resumes by re-invoking — typically `/bmad-auto --epics K` in
     Express mode so they can engage with the tracer directly.
4. **Derive Stage 3.4 polling cadence.** Compute `story_count` as the
   length of the non-tracer story list from step #3 (Headless includes
   K-1, so its `story_count` is naturally one higher). Delegate the
   tiered lookup to the helper:

   ```sh
   cadence_seconds=$(scripts/bmad-auto-helper.py derive-cadence \
     --story-count "$story_count")
   ```

   Helper emits a bare integer to stdout (no JSON wrapping) and is the
   source of truth for the tier breakpoints. The cadence is **derived
   once here** and stable for the whole run; no runtime re-derivation.
   Record a one-line note to orchestrator-session memory:
   `cadence: <N>s for <K> stories`. Persist the integer (single line,
   no trailing prose) to `_bmad-output/.run-state/cadence-<runId>.txt`
   for Stage 4.e digest reference.
5. If list is empty: print *"No stories remain for epic K. Proceeding
   to Phase 4."* Skip to Phase 4.

### Stage 3 — Per-story loop

For each `<storyId>` in the story list (sequential):

#### 3.1 — Compose the per-story directive (two-message protocol)

**Story-file handling contract (Phase 3 delegation):** Unlike Stage
2.a (which passes a story file path to `bmad-testarch-atdd`), Phase
3's per-story fanout passes the **storyId as the authoritative
binding key** to `bmad-quick-dev` via the per-story directive (a
two-message paste: short `/goal` intent + plain-prompt directives).
The directive also includes a `Story file path:` hint, but the
storyId is what governs — quick-dev's step-01-clarify-and-route
resolves the spec natively: if a file exists at the hinted path it
resumes from that spec; if only a skeleton exists in `epics.md`,
it compiles epic context (`epic-K-context.md` cached in
implementation-artifacts) and generates the spec in step-02.
`/bmad-auto` does NOT pre-flight check for per-story files in
Stage 3 setup or Stage 3.1 — the delegation is unconditional.
(Stage 1.a guarantees per-story files exist for the epic before
Phase 2 launches; that guarantee is for Stage 2.a's ATDD
invocation, not Stage 3.)

The per-story directive is sent as **two sequential tmux pastes**
with ~3s between them (helper's `cmd_spawn`, post-v5-fix-3). The
split is required because Claude Code v2 enforces a 4000-char
ceiling on `/goal` payloads, and the verbatim autonomous-mode
directives file alone is ~5KB. The spawn-boundary verbatim-survival
principle is preserved — the directive content still crosses as
inlined text via tmux paste-buffer — only the *mechanism* changed
from one `/goal` payload to a plain-prompt sibling. Provenance:
bmad-auto-v5-smoke-fix-3.md.

**Message 1 — short `/goal` (intent + binding; must stay under 4000 chars):**

```
/goal Story <storyId> of epic K has status: <current-status> in sprint-status.yaml.
Execute via bmad-testarch-atdd (red-phase scaffolds) THEN bmad-quick-dev
(implementation makes red green) THEN bmad-testarch-automate (or
bmad-qa-generate-e2e-tests for coverage expansion, non-blocking) THEN
bmad-code-review.

Story file path: <path to K-<storyId>-<slug>.md>
Architecture: <path to epic-K-micro-architecture.md under Format A,
              or _bmad-output/planning-artifacts/architecture.md
              under Format A-equivalent (the default for single-epic
              projects)>
ATDD checklist: bmad-testarch-atdd writes the checklist to its
                canonical path
                _bmad-output/test-artifacts/atdd-checklist-<story_key>.md
                (where <story_key> is the story filename's .md-less
                stem). Do not attempt to override the output path.
                Quick-dev should locate it via the glob
                _bmad-output/test-artifacts/atdd-checklist-K-<storyId>-*.md.

Mark sprint-status.yaml story key to `done` only when:
- ATDD red tests authored
- bmad-quick-dev makes them green AND produces clean implementation
- code-review passes
- (optional, non-blocking) coverage-expansion ran
```

Save to `${TMPDIR:-/tmp}/bmad-auto-goal-<runId>-<storyId>.txt`.

**Message 2 — plain prompt (autonomous-mode directives, verbatim; no `/goal` prefix):**

```
Apply these 8 autonomous-mode directives verbatim throughout
the goal above. Then proceed: ATDD → quick-dev → coverage-
expansion → code-review.

<verbatim contents of references/autonomous-mode-directives.md>
```

Save to `${TMPDIR:-/tmp}/bmad-auto-directives-<runId>-<storyId>.txt`.

#### 3.2 — Spawn the per-story tmux session

Delegate the spawn to the helper's `spawn` subcommand. It composes
the session name (`auto-K-<storyId>-<runId>`), starts the tmux session
running `claude --dangerously-skip-permissions`, applies the spawn-
warmup contract (below), then pastes the **two** per-story directive
messages via load-buffer / paste-buffer / send-keys (short `/goal`
first, plain-prompt directives second). The single-sequence form was
validated byte-exact in D4; the second sequence mirrors it.

```sh
scripts/bmad-auto-helper.py spawn \
  --story-id "<storyId>" \
  --run-id "<runId>" \
  --goal-file "${TMPDIR:-/tmp}/bmad-auto-goal-<runId>-<storyId>.txt" \
  --directives-file "${TMPDIR:-/tmp}/bmad-auto-directives-<runId>-<storyId>.txt"
```

**Spawn-warmup contract (load-bearing against Claude Code v2.1.153+).**
The helper interleaves three settle delays + one trust-prompt dismissal
into the spawn flow. All three are configurable via CLI flags but the
defaults are the validated values; lowering them risks re-introducing
the production stall described below.

| Step | Default | Purpose |
| --- | --- | --- |
| `tmux new-session ... claude --dangerously-skip-permissions` | — | Spawn claude |
| Sleep `--claude-boot-wait-seconds` | **10.0** | Let claude render welcome banner + workspace-trust prompt before any input arrives |
| `send-keys Enter` | — | Dismiss workspace-trust prompt (default selection is "Yes, I trust this folder"); no-op when the dir is already trusted |
| Sleep `--trust-prompt-settle-seconds` | **3.0** | Let the trust dialog dismiss + input box settle to the idle prompt |
| `load-buffer` + `paste-buffer` (Message 1) | — | Short `/goal` payload |
| Sleep `--paste-to-submit-settle-seconds` | **2.0** | Required when Claude Code v2 folds the paste into `[Pasted text #N +M lines]` placeholders; without it, the `C-m` is silently swallowed and the paste sits unsubmitted |
| `send-keys C-m` | — | Submit Message 1 |
| Sleep `--inter-message-delay-seconds` | **3.0** | Let claude accept the `/goal` before Message 2 arrives |
| `load-buffer` + `paste-buffer` (Message 2) | — | Verbatim autonomous-mode-directives |
| Sleep `--paste-to-submit-settle-seconds` | **2.0** | Same rationale as Message 1 |
| `send-keys C-m` | — | Submit Message 2 |

**Why the warmup contract exists.** Empirically discovered 2026-05-28:
without the boot wait, the first paste lands during claude's still-
rendering UI and the subsequent `C-m` gets eaten by the trust-prompt
menu or welcome screen; without the paste-to-submit settle, Claude
Code v2's auto-folding of long pastes into placeholders defers
re-render past the moment `C-m` arrives, so submit is dropped and
the paste sits in the input box. Either failure mode leaves the
per-story session alive but stuck — Stage 3.4 detects this as a
stall after the warmup-grace window. Total added latency per spawn:
~17 seconds. Regression coverage in
`scripts/tests/test_spawn_two_message_split.py`.

On success the helper prints a single line of JSON to stdout:
`{"session_name": "auto-K-<storyId>-<runId>", "spawned_at": "<UTC ISO>"}`.
Record `session_name` for Stage 3.4 polling. On failure (tmux missing,
goal-file or directives-file missing, session-name collision, or any
failure during the warmup / load-buffer / paste-buffer / send-keys
sequence), the helper exits non-zero with a stderr message and best-
effort cleans up any half-spawned session — HALT the run and surface
the error.

#### 3.4 — Monitor the per-story session

Delegate polling, HALT detection, and stall fingerprinting to the
helper's `monitor` subcommand. It runs the cadence-controlled poll
loop, treats the sprint-status flip as the authoritative completion
signal, reads the
`_bmad-output/.run-state/quick-dev-halt-<storyId>.json` sidecar
ahead of any capture-pane heuristic (per directive #8 in
`references/autonomous-mode-directives.md`), applies the structural
guards to the grep-on-pane fallback, fingerprints capture-pane for
stall detection, and enforces a 60-minute wall-clock timeout. The
helper blocks until one terminal state is reached and emits a single
line of JSON.

```sh
result=$(scripts/bmad-auto-helper.py monitor \
  --session "auto-K-<storyId>-<runId>" \
  --story-id "<storyId>" \
  --run-id "<runId>" \
  --cadence-seconds "$cadence_seconds" \
  --sidecar-path "_bmad-output/.run-state/quick-dev-halt-<storyId>.json")
final_state=$(echo "$result" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["final_state"])')
```

**Grep warmup grace (default 2 polls).** The helper's `monitor` subcommand
accepts an optional `--grep-warmup-polls <N>` flag (default `2`,
`~90s` at the 45s cadence tier). During polls `1..N` the capture-pane
grep fallback is suppressed entirely — sidecar primary still runs every
poll, including during warmup, so any sidecar-emitted HALT is detected
without delay. Rationale: a freshly-spawned per-story session's pane is
dominated by the pasted per-story directive prose (specifically the
verbatim autonomous-mode-directives plain-prompt second message of
the two-message protocol — directive 8's
`intent_gap | bad_spec | loopback_overflow | ...` enumeration and
directive 5's `` `>5 loopbacks on one story` `` phrase). The structural
guards do not suppress every bare trigger substring inside that prose,
so grep at poll #1 false-positives on the directive itself. The warmup
grace gives the spawned claude two polls' worth of pane output to scroll
the directive off before grep is trusted. Provenance:
`bmad-auto-v5-smoke-fix-1.md`.
Operators who want grep enabled from poll #1 (e.g. for sidecar-less
debugging) can pass `--grep-warmup-polls 0`.

`final_state` is exactly one of: `completed | halted | stalled | timeout`.

- `completed` — sprint-status.yaml flipped to `done` for `<storyId>`.
  The helper has already killed the tmux session. Run
  `git rev-parse HEAD` and record to
  `_bmad-output/.run-state/epic-K-story-<storyId>-end.sha` (for Phase 4
  Codex per-story scope if `--per-story-codex` is set). Log
  `K-<storyId>: done` to orchestrator memory. Continue to the next
  story (or to Stage 3.5 if `--per-story-codex`).
- `halted` — sidecar present and valid, or a capture-pane candidate
  passed all structural guards. The helper has already killed the
  session and written full pane output to
  `_bmad-output/.run-state/epic-K-story-<storyId>-halt-context.txt`.
  The result JSON also carries `halt_class` (one of `intent_gap |
  bad_spec | vcs_dirty | wrong_branch | loopback_overflow |
  halt_literal | red_tests_failing`), `halt_reason`, and `halt_source`
  (`sidecar` or `grep`) for Stage 4.e digest composition. Proceed to
  Stage 3.C.2 HALT-exit branching.
- `stalled` — capture-pane fingerprints went identical across the
  configured rolling window after the warmup, with no sprint-status
  flip and no HALT. The helper has NOT killed the session (the
  operator may want to attach). Full pane is at
  `_bmad-output/.run-state/epic-K-story-<storyId>-stall-context.txt`.
  Proceed to Stage 3.C.3 STALL-exit branching.
- `timeout` — 60 minutes of wall-clock elapsed without a terminal
  state. The helper has NOT killed the session (operator triage
  required) and emits a stderr warning. Proceed to Stage 3.C.4
  TIMEOUT-exit branching.

Sprint-status flip is the authoritative completion signal; any
printed marker the spawned claude emits is advisory secondary signal
only — never primary (per the G3v4 false-positive). The per-story
directive is responsible for emitting the sprint-status flip; if it
does not, the helper's stall layer surfaces the session as `stalled`.

#### 3.5 — Per-story Codex (if `--per-story-codex`)

Gated invocation: only run if `--per-story-codex` flag is set AND
`codex_available=true` AND the story exited cleanly (sprint-status flip
to `done`, no HALT, no stall). On skip, no output file is produced.

**Detect git vs non-git** before composing the invocation — mirrors the
Stage 4.c fork (D13v4). Run `git rev-parse --is-inside-work-tree 2>/dev/null`.
Equivalent sidecar-presence signal: per-story `epic-K-story-<storyId>-end.sha`
(git path, recorded by Stage 3.4 on sprint-status flip) vs epic-wide
`epic-K-start.paths` (non-git path, recorded by Stage 3 setup #1).

**Invocation flag-set verified against codex-cli 0.124.0** (same pin as
Stage 4.c, recorded in `_bmad-output/.run-state/codex-version.txt` at
Stage 0.4). Same structural constraints apply: `codex review` accepts
diff input via `--uncommitted` / `--base <BRANCH>` / `--commit <SHA>`
only — all three require a git repository, and there is no
`--range <A>..<B>` mode. The git path uses the same synthetic-branch
workaround as Stage 4.c, parameterized per story so concurrent runs do
not collide.

**Git path (preferred — full per-story diff fidelity):**

The per-story diff range is `<prev>..<storyId>-end.sha`, where `<prev>`
is `epic-K-start.sha` for the first story in the loop and
`<prev-storyId>-end.sha` for subsequent stories.

```sh
# Create a per-story synthetic branch at <prev-sha> for codex's --base
# input. Branch name is unique per story + run to keep concurrent
# per-story reviews from colliding.
git branch bmad-auto-codex-base-<runId>-<storyId> <prev-sha>

# Invoke codex review with positional prompt + --base flag
codex review --base bmad-auto-codex-base-<runId>-<storyId> "<adversarial prompt>"

# Clean up synthetic branch
git branch -d bmad-auto-codex-base-<runId>-<storyId>
```

The synthetic-branch workaround bridges the SHA-range gap in
`codex review`. It is inherently git-only and does not run on the
non-git path.

**Non-git path (degraded — paths-only review, no diff baseline,
epic-wide path scope):**

`codex review` has no input mode that accepts a pre-computed diff or
a list of paths outside a git repo. The viable fallback is `codex exec`
with `--skip-git-repo-check`, treating the per-story adversarial
review as a freeform inspection of the listed paths.

```sh
# Read touched paths from the Stage 3 setup #1 epic-wide sidecar
# (file format: shell comments + one relative path per line). No
# per-story sidecar exists under the non-git path today — see the
# noted-degradation block + follow-up flag below.
paths=$(grep -v '^#' _bmad-output/.run-state/epic-K-start.paths \
        | grep -v '^[[:space:]]*$')

# Compose a paths-aware story-scoped adversarial prompt and invoke
# codex exec.
# `--skip-git-repo-check` lets codex run outside a git workspace;
# `--sandbox read-only` keeps it from mutating files;
# `-c approval_policy=never` keeps it non-interactive (config override;
# `--ask-for-approval` is a `codex` top-level flag, not a `codex exec`
# flag — verified against codex-cli 0.124.0).
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  -c approval_policy=never \
  "<adversarial prompt with the path list embedded verbatim>"
```

The embedded prompt must list the paths explicitly and instruct codex
to read each one and review them as a unit against the current story's
acceptance criteria + tracer-architecture integration points. Codex
cannot compute a diff in this mode — review is against the current
file contents only, and the path list is epic-wide (over-collects for
per-story scope).

**Noted degradation — non-git path is doubly weaker than the git
path:**

1. **No diff baseline.** Codex sees post-implementation state only;
   cannot isolate this story's changes from prior stories'.
2. **Path scope is epic-wide, not story-scoped.** The available
   sidecar (`epic-K-start.paths`) is produced once for the epic by
   Stage 3 setup #1. There is no `epic-K-story-<storyId>-start.paths`
   producer today, so the non-git per-story review reads the same
   path list every story.

Concern #1 weakens (same as Stage 4.c). Concern #2 widens the review
beyond per-story scope but cannot fabricate findings — extra context
weakens focus, not soundness. Record this degradation in the output
header (see Output below).

**Adversarial prompt — story-scoped concerns (under either path):**

1. **Per-AC coverage.** Did the implementation satisfy every
   acceptance criterion in the story file, especially edge cases?
2. **Integration-point alignment with tracer.** The architecture
   artifact from Phase 1 (micro-architecture under Format A, or the
   whole-project `architecture.md` under Format A-equivalent) is the
   contract — did the story's changes conform at integration
   boundaries with prior stories (especially K-1, the tracer)?

Do NOT substitute the epic-wide three-concerns prompt from Stage 4.c
here — Stage 3.5 is story-scoped by design; Stage 4.c handles the
epic-wide cross-story consistency pass.

**Runtime introspection hedge:** before invoking, run
`codex review --help` (git path) or `codex exec --help` (non-git
path) and verify the flags above still exist. If codex's CLI surface
has drifted, adapt — but the SHA-range gap (git path) and the
no-paths-review-mode gap (non-git path) are structural, not flag-name
issues (per D3 findings + D13v4 verification against codex-cli
0.124.0; D15.5v4 inherits the same surface).

Output: `_bmad-output/implementation-artifacts/epic-K-story-<storyId>-codex-review.md`
(header: epic K, storyId, runId, UTC timestamp, mode tag `git` or
`non-git`, per-story diff range (git) OR epic-wide path list (non-git,
with explicit "epic-wide scope" noted-degradation flag), invocation
command verbatim, then verbatim Codex output).

### Stage 3.C — Loop exit branching

After the per-story loop completes:

- **3.C.1 Natural exit** (all non-tracer stories now `done`):
  Proceed to Phase 4.
- **3.C.2 HALT exit** (any story HALTed during 3.4):
  - Skip Phase 4a (quality gate trace) — partial diff produces noise.
  - Skip Phase 4b (NFR audit) — same reason.
  - Skip Phase 4c (Codex) — partial diff is noisy for adversarial review.
  - Skip Phase 4d (deferred-work delta) — same reason.
  - DO proceed to Phase 4e (digest) so the operator gets context on
    what completed + what halted.
  - DO skip Phase 4f (retrospective) — partial run isn't ready for
    retrospective.
- **3.C.3 STALL exit** (any story stalled during 3.4 per the
  stall-detection layer):
  - Do NOT kill the stalled tmux session automatically. Surface it to
    the operator as a banner + action menu (per *Operator presentation
    conventions*):

    ```
    ═══════════════════════════════════════════════════════════
    ⚠️  STORY <id> STALLED — Epic K · auto-K-<id>-<runId>
    ═══════════════════════════════════════════════════════════
       idle <elapsed wall-clock since spawn>
       context: _bmad-output/.run-state/epic-K-story-<storyId>-stall-context.txt

      Code  Action
      N     Nudge       attach, send a brief nudge enumerating terminal actions, detach, re-poll
      D     Drive       attach and finish the story yourself; next poll picks up the sprint-status flip
      K     Kill+rerun  kill the session, re-run `/bmad-auto --epics K` to resume from sprint-status
      H     Halt        treat as an explicit HALT → falls through to 3.C.2 (digest only, skip gates/retro)

    Stop and wait for input. Accept a number, code, or fuzzy match.
    ```
  - Treat the run as paused. Do not advance into Phase 4 until the
    operator resolves the stall by either driving the session to
    `done` (re-enter the per-story loop, which will pick up the
    sprint-status flip on next poll) or explicitly HALTing it (in
    which case fall through to 3.C.2 behavior).
  - Rationale: stall ≠ HALT, and silently advancing past a stalled
    session would corrupt accounting (sprint-status still shows the
    story as not-done, but the orchestrator has moved on).
- **3.C.4 TIMEOUT exit** (any story timed out during 3.4 — helper
  emitted `final_state: timeout` after the 60-minute wall-clock
  budget elapsed without a terminal state):
  - Do NOT kill the timed-out tmux session automatically. Surface it
    with the same banner + action menu, noting that a timed-out session
    may be progressing slowly rather than frozen — so inspect before
    killing:

    ```
    ═══════════════════════════════════════════════════════════
    ⚠️  STORY <id> TIMED OUT — Epic K · auto-K-<id>-<runId>
    ═══════════════════════════════════════════════════════════
       exceeded 60-min wall-clock budget · may be progressing slowly — inspect before killing
       attach: tmux attach -t auto-K-<id>-<runId>

      Code  Action
      N     Nudge       attach, inspect what's stuck, nudge it to completion, detach, re-poll
      D     Drive       attach and finish the story yourself; next poll picks up the sprint-status flip
      K     Kill+rerun  kill the session, re-run `/bmad-auto --epics K` to resume from sprint-status
      H     Halt        treat as an explicit HALT → falls through to 3.C.2 (digest only, skip gates/retro)

    Stop and wait for input. Accept a number, code, or fuzzy match.
    ```
  - Treat the run as paused. Do not advance into Phase 4 until the
    operator resolves the timeout (driving the session to `done`
    re-enters the per-story loop via the next sprint-status poll;
    explicit HALT falls through to 3.C.2 behavior).
  - Rationale: a timeout is "session is alive but exceeded its
    bounded wall-clock budget", structurally similar to STALL.
    Distinct from STALL only in that the helper's fingerprint layer
    didn't fire — useful diagnostic signal for the operator (e.g.
    the session may be slowly progressing rather than fully frozen).
---

## Phase 4 — End HITL (Express + Headless + Guided `--dev`)

### Stage 4.a — Quality gate: traceability

Skip on HALT exit (per 3.C.2).

Invoke `bmad-testarch-trace`. Inputs: epic K test files + ACs from
epics.md / story files.

Output:
- `_bmad-output/implementation-artifacts/epic-K-traceability-matrix.md`
- `_bmad-output/implementation-artifacts/epic-K-e2e-trace-summary.json`
- `_bmad-output/implementation-artifacts/epic-K-gate-decision.json`

**Read-side validation (runtime drift guard).** TEA's producer-side
output schemas are not pinned upstream, so before trusting the gate
verdict, validate `epic-K-gate-decision.json`: (1) file exists at the
expected path, (2) parses as JSON without syntax error, (3) a top-level
`gate_status` field is present, (4) its value is one of `PASS`,
`CONCERNS`, `FAIL`, or `WAIVED` (case-sensitive — TEA emits uppercase).

On any failure, HALT with: *"`bmad-testarch-trace` produced
`gate-decision.json` but the expected `gate_status` field is missing or
has an unrecognized value (`<actual>`). This typically means TEA's
output schema drifted; check `{project-root}/_bmad/tea/config.yaml` for version and
the canonical `step-05-gate-decision.md` for the current field set.
Halting the run rather than silently reporting an unknown gate."* Do
NOT fall back to a cached prior value — HALT is the only correct
response to drift. On the happy path, pass `gate_status` through
unchanged to the record step below.

Record the gate status (PASS / CONCERNS / FAIL / WAIVED) to
`_bmad-output/.run-state/epic-K-trace-gate.txt`.

### Stage 4.b — Quality gate: NFR audit

Skip on HALT exit. Skip if no NFR-touching code in the epic diff.

Invoke `bmad-testarch-nfr`. Inputs: implementation evidence (test
results, scans, metrics, logs), NFR thresholds (from test-design if
ran in 1c).

Output: `_bmad-output/implementation-artifacts/epic-K-nfr-assessment.md`.

**Post-invocation parse → canonical sidecar (drift containment).** TEA
ships the NFR verdict only inside a markdown report and does not pin
the report shape upstream. Parse `epic-K-nfr-assessment.md` exactly
once here and write a machine-readable sidecar at
`_bmad-output/.run-state/epic-K-nfr-decision.json` with this shape:

```json
{
  "status": "<PASS | CONCERNS | FAIL>",
  "evidence_summary": "<one-line summary from the markdown, or null>",
  "parsed_at": "<UTC ISO 8601 timestamp>",
  "source": "epic-K-nfr-assessment.md",
  "parser_version": "1"
}
```

This sidecar is the SINGLE source of NFR status for every downstream
stage (notably Stage 4.e digest). Do not let any other stage re-parse
the markdown for status — the markdown remains the operator-readable
artifact, the sidecar is the machine contract.

Parsing strategy, in order of preference:

1. Locate the **`## Gate YAML Snippet`** section (rendered header per
   `nfr-report-template.md`; step prose at
   `.claude/skills/bmad-testarch-nfr/steps-c/step-05-generate-report.md`
   refers to it as the "Gate-ready YAML snippet"). Parse the fenced
   ` ```yaml ` block beneath the header and read the
   `nfr_assessment.overall_status` field.
2. Fall back to a regex grep for an explicit status line near the
   report tail: `^\*\*Gate Status:\*\*\s+(PASS|CONCERNS|FAIL)`,
   `^Gate Status:\s+(PASS|CONCERNS|FAIL)`, or
   `^Status:\s+(PASS|CONCERNS|FAIL)` (first match wins).
3. If both strategies fail, set `status: "UNKNOWN"` in memory and
   HALT with: *"`bmad-testarch-nfr` produced
   `epic-K-nfr-assessment.md` but the parser could not locate a gate
   status via the `Gate YAML Snippet` block or a `Gate Status:` line.
   This typically means TEA reformatted the report; check
   `{project-root}/_bmad/tea/config.yaml` for version and the canonical
   `step-05-generate-report.md` / `nfr-report-template.md` for the
   current section names. Halting rather than propagating UNKNOWN
   into the digest."* HALT-on-UNKNOWN is intentional — silent UNKNOWN
   would corrupt Stage 4.e.

The `status` enum is case-sensitive and bounded to `PASS | CONCERNS |
FAIL` (no `WAIVED` for NFR — that value is trace-only). Keep
`parser_version: "1"` literal; bump only when this contract changes
so future parser-tolerant downstream consumers can branch on version.

`evidence_summary` is best-effort: take the first non-empty line under
the report's `## Executive Summary` section if present (typically the
`**Assessment:** N PASS, M CONCERNS, P FAIL` line), otherwise set the
field to `null`. Do not HALT on evidence-summary extraction failure —
it is a digest nicety, not load-bearing.

Then record the gate status (PASS / CONCERNS / FAIL) to
`_bmad-output/.run-state/epic-K-nfr-gate.txt` by writing the sidecar's
`status` field. The `.txt` file remains the single-line gate-status
artifact for shell-friendly consumers; the sidecar is for stages that
need the full structured record.

Skip-on-conditional behavior is unchanged: if NFR was skipped because
no NFR-touching code is present in the epic diff, neither the sidecar
nor `epic-K-nfr-gate.txt` is written — same as today.

### Stage 4.c — Codex adversarial review

Skip on HALT exit. Skip if `codex_available=false` (write
`_bmad-output/.run-state/epic-K-codex-skipped.txt` with reason).

**Detect git vs non-git** before composing the invocation. Run
`git rev-parse --is-inside-work-tree 2>/dev/null`. Branch accordingly.
Equivalent signal: presence of `epic-K-start.sha` (git path) vs
`epic-K-start.paths` (non-git path) from Stage 3 setup #1.

**Invocation flag-set verified against codex-cli 0.124.0** (pin recorded
in `_bmad-output/.run-state/codex-version.txt` at Stage 0.4). The
original SKILL.md's `git diff <start-sha>..<end-sha> | codex review --stdin --prompt "<prompt>"` is **structurally wrong** for real codex. Real `codex review` accepts diff input via `--uncommitted` / `--base <BRANCH>` / `--commit <SHA>` only — all three require a git repository. Prompt is a positional argument, not a `--prompt` flag.

**Drift note (codex-cli 0.124.0 observed 2026-05-28):** `codex review --uncommitted` and a positional `[PROMPT]` argument are **mutually exclusive** — the CLI rejects with `error: the argument '--uncommitted' cannot be used with '[PROMPT]'`. This blocks the naive `codex review --uncommitted "<adversarial prompt>"` form. Use the **git path synthetic-branch + `--base`** invocation below (which keeps the positional prompt) when there is a non-empty diff range. When `epic-K-start.sha == epic-K-end.sha` (working-tree-only changes, no commits), fall back to **`codex exec --skip-git-repo-check`** with the prompt embedded — same as the non-git path below. Record the mode tag in the output header so postmortem readers know which input mode was used.

**Git path (preferred — full diff fidelity):**

```sh
# Create a synthetic branch at <start-sha> for codex's --base input
git branch bmad-auto-codex-base-<runId> <epic-K-start.sha>

# Invoke codex review with positional prompt + --base flag
codex review --base bmad-auto-codex-base-<runId> "<adversarial prompt>"

# Clean up synthetic branch
git branch -d bmad-auto-codex-base-<runId>
```

The synthetic-branch workaround bridges the SHA-range gap in
`codex review` (which has no `--range <A>..<B>` mode). It is
inherently git-only and does not run on the non-git path.

**Non-git path (degraded — paths-only review, no diff baseline):**

Real codex 0.124.0 has no input mode that accepts a pre-computed
diff or a list of paths through `codex review`. The viable fallback
is `codex exec` with `--skip-git-repo-check`, treating the
adversarial review as a freeform inspection of the listed paths.

```sh
# Read touched paths from the Stage 3 setup #1 sidecar
# (file format: shell comments + one relative path per line)
paths=$(grep -v '^#' _bmad-output/.run-state/epic-K-start.paths \
        | grep -v '^[[:space:]]*$')

# Compose a paths-aware adversarial prompt and invoke codex exec.
# `--skip-git-repo-check` lets codex run outside a git workspace;
# `--sandbox read-only` keeps it from mutating files;
# `-c approval_policy=never` keeps it non-interactive (config override;
# `--ask-for-approval` is a `codex` top-level flag, not a `codex exec`
# flag — verified against codex-cli 0.124.0).
codex exec \
  --skip-git-repo-check \
  --sandbox read-only \
  -c approval_policy=never \
  "<adversarial prompt with the path list embedded verbatim>"
```

The embedded prompt must list the paths explicitly and instruct
codex to read each one and review them as a unit. Codex cannot
compute a diff in this mode — review is against the current
file contents only. Record this degradation in the output header
(see Output section below). Non-git inherits the path list from
Stage 3 setup #1's `epic-K-start.paths` (which is derived from
`epic-K-micro-architecture.md` under Format A, or from the whole-
project `architecture.md` under Format A-equivalent — the latter
over-collects, which is acceptable for adversarial review since
extra context cannot produce false-positive findings, only weaker
focus).

The adversarial prompt — under either path — focuses on three
concerns:

1. **Integration drift from tracer architecture.** Whichever
   format (A or A-equivalent) is in use, the architecture artifact
   is the contract. Did the diff conform?
2. **Cross-story inconsistency.** Patterns, interfaces, naming
   should be consistent across stories landed in this run.
3. **Missed acceptance-criterion edges.** Each story's ACs — did the
   implementation satisfy them, especially edge cases?

Under the non-git path, concern #1 weakens (no diff baseline; codex
sees post-implementation state only) and concerns #2 + #3 remain
fully applicable.

**Runtime introspection hedge:** before invoking, run
`codex review --help` (git path) or `codex exec --help` (non-git
path) and verify the flags above still exist. If codex's CLI surface
has drifted, adapt — but the SHA-range gap (git path) and the
no-paths-review-mode gap (non-git path) are structural, not
flag-name issues (per D3 findings + D13v4 verification against
codex-cli 0.124.0).

Output: `_bmad-output/implementation-artifacts/epic-K-codex-review.md`
(header: epic K, runId, UTC timestamp, mode tag `git` or `non-git`,
diff range OR path list, invocation command verbatim, detected
tracer-architecture format, then verbatim Codex output).

### Stage 4.d — Deferred-work delta

Skip on HALT exit.

1. Read `_bmad-output/.run-state/deferred-work-start.snapshot` (from
   Stage 3 setup step 2).
2. Read current state of
   `_bmad-output/implementation-artifacts/deferred-work.md`.
3. Compute delta — new entries added during the run.
4. Classify each new entry per `references/deferred-classifier.md`
   markers (scope-split / review-finding / ambiguous). Per D2 fixtures
   + D7 tuning.
5. Write `_bmad-output/implementation-artifacts/epic-K-deferred-delta.md`
   with sections: Scope-split / Review-finding / Ambiguous + counts.

### Stage 4.e — Digest render

The digest is the operator-facing summary. Aim for ~40–50 lines total
(adjusted from prior ~35–40 to accommodate quality-gate sections per
D5 deviation #1).

Read sidecars (skip-tolerant — files may be absent on HALT exit):

- `epic-K-start.sha`, `epic-K-end.sha` (or `.paths` fallback)
- `epic-K-trace-gate.txt`
- `epic-K-nfr-decision.json` (canonical NFR sidecar per Stage 4.b —
  read `status` for the verdict and `evidence_summary` for the
  one-line summary; the parallel `epic-K-nfr-gate.txt` exists for
  shell-friendly consumers but the digest reads the JSON. Absent
  sidecar means NFR was conditionally skipped — render N/A
  unchanged.)
- `epic-K-codex-review.md` (for link)
- `epic-K-codex-skipped.txt` (if codex was unavailable)
- `epic-K-deferred-delta.md`
- `quick-dev-halt-<storyId>.json` (HALT-exit only, sidecar-primary
  path — when the helper's sidecar-read fired the HALT (i.e.
  `halt_source: sidecar` in the Stage 3.4 `monitor` result), this
  JSON is the preferred source for HALT context: surface `reason`
  and `files_affected` verbatim in the digest's HALT block)
- `epic-K-halt-context.txt` (HALT-exit only; tail to last ~15 lines per
  D5 deviation #1 to honor one-screen budget — used when grep-on-pane
  fallback fired the HALT, OR when the sidecar JSON is absent/malformed)
- `epic-K-phase1-findings.json` (Phase 1.e hybrid hardening: parallel-scan findings + per-finding triage outcomes)

**Composition layout (canonical, natural / HALT exits).** Open with
an end-HITL banner and prefix the Status line and each gate verdict
with its status badge per *Operator presentation conventions* (`✅`
PASS/WAIVED/completed · `⚠️` CONCERNS · `🚨` FAIL/HALTED; `N/A` and
`Skipped` take no badge). Badges + banner are the only additions — the
field set, ordering, and ~40–50 line budget are unchanged:

```
═══════════════════════════════════════════════════════════
🏁  EPIC K — <epic-title-from-epics.md>
═══════════════════════════════════════════════════════════
runId <runId>

Status: <✅ Completed naturally | 🚨 HALTED at story <id>>
Mode: <Express | Headless | Guided>
Duration: <hh:mm>
Stories: <K-1 (tracer) + K-2..K-N if completed>

Quality gates:
  Traceability: <badge> <PASS | CONCERNS | FAIL | WAIVED> (see epic-K-traceability-matrix.md)
  NFR audit:    <badge> <PASS | CONCERNS | FAIL | N/A> (see epic-K-nfr-assessment.md)
                <if sidecar `evidence_summary` is non-null:>
                  Evidence: <epic-K-nfr-decision.json `evidence_summary`>

Codex review: <link to epic-K-codex-review.md> | <Skipped — codex unavailable> | <Skipped — launch halted>

Deferred-work delta: <N scope-split + M review-finding + P ambiguous> | <Skipped — launch halted>

Tracer docs: <full path to micro-PRD + micro-architecture (Format A) or whole-project architecture.md (Format A-equivalent)>

HALT context (HALT exit only):
    <when sidecar fired (preferred):>
      Status:         <quick-dev-halt-<storyId>.json `status`>
      Reason:         <quick-dev-halt-<storyId>.json `reason`>
      Files affected: <quick-dev-halt-<storyId>.json `files_affected`, comma-joined or "none">
    <when grep-on-pane fallback fired (sidecar absent/malformed), last 15 lines:>
      <indented tail of epic-K-halt-context.txt>

Phase 1 hardening: <N resolved + M deferred + P split-off> (see epic-K-phase1-findings.json if non-empty)

Next steps:
- Review the diff. Files touched: <list or summary>.
- Run `bmad-checkpoint-preview` for human walk-through.
- <if natural exit:> Phase 4f will auto-spawn `bmad-retrospective`. Engage with party-mode dialogue.
- <if HALT exit:> Resolve HALT manually (see context above) and re-invoke `/bmad-auto --epics K`.
- Next backlog epic: <next-K> (per sprint-status.yaml)
```

**Next-backlog-epic lookup:** read sprint-status.yaml. Enumerate
distinct epic-number prefixes from `development_status` keys. Filter
to backlog epics (at least one story not `done`) strictly greater than
K. Pick lowest. If none: print *"No more backlog epics."*

Print to terminal AND save byte-for-byte identical content to
`_bmad-output/.run-state/run-digest-<runId>.md`.

### Stage 4.f — Auto-spawn retrospective

Skip on HALT exit. Skip in Headless mode unless `--with-retrospective`.

Invoke `bmad-retrospective` for epic K. Heavy interactive — party-mode
multi-agent dialogue. The skill detects K from sprint-status (highest
epic with all stories done) and confirms with operator.

When retrospective completes:
- Sprint-status is updated (retrospective key → `done`)
- `epic-K-retro-<date>.md` written
- Check the retro output for **significant discoveries** signal (Step 8)
  and **critical readiness** assessment (Step 9). Record both to
  `_bmad-output/.run-state/epic-K-retro-signals.txt`.

### Stage 4.g — Conditional correct-course

Skip on HALT exit.

Read `_bmad-output/.run-state/epic-K-retro-signals.txt`. If
significant-discoveries flag was set OR critical-readiness status is
FAIL, prompt operator:

> Retrospective surfaced potential next-epic blockers:
>   - <signal 1>
>   - <signal 2>
>
> Run `/bmad-correct-course` to address before next epic? `[Y/n]`

On `y`: auto-invoke `bmad-correct-course` for the next backlog epic.
On `n`: log decision and exit cleanly.

In Headless mode: log signals but do not auto-prompt; operator reviews
post-hoc.

### Stage 4 exit

Print final completion message:

> Epic K complete. Digest at `_bmad-output/.run-state/run-digest-<runId>.md`.
> <if retrospective ran:> Retrospective at
> `_bmad-output/implementation-artifacts/epic-K-retro-<date>.md`.
> Next backlog epic: <next-K> (run `/bmad-auto --epics <next-K>` when
> ready).

Exit. Do NOT loop into next epic. Every epic-to-epic transition is
operator-explicit.

---

## Compaction-resilience non-negotiables

Carried forward from
[docs/auto-skills-design.md](docs/auto-skills-design.md):

1. **Per-story isolation.** Each story in Phase 3 runs in a fresh
   tmux-spawned `claude --dangerously-skip-permissions` process. The
   orchestrator session does NOT carry per-story transcripts forward.
   Only one-line statuses (`K-2: done`, `K-3: HALTED at intent_gap`)
   accumulate.

2. **Sidecar-driven state.** All cross-stage / cross-phase persistence
   uses files in `_bmad-output/.run-state/` and
   `_bmad-output/implementation-artifacts/`. Orchestrator-session
   memory never holds raw artifact content — only file paths and
   one-line status notes.

3. **Sequential per-story.** No parallel execution within an epic.
   Per Alex's "sequential inside each [epic]." Parallel across epics
   is operator-driven (separate `/bmad-auto --epics K` invocations).

4. **Read fresh.** Sprint-status is the source of truth for story
   state. Re-read on every poll cycle; never cache.

---

## Sidecar file index

| File | Producer | Consumer |
| --- | --- | --- |
| `_bmad-output/.run-state/codex-version.txt` | Stage 0.4 | Stage 4.c |
| `_bmad-output/.run-state/architecture-mode.txt` | Stage 0.8 | Stage 1.a |
| `_bmad-output/.run-state/epic-K-phase1-findings.json` | Stage 1.e | Stage 4.e digest |
| `_bmad-output/.run-state/epic-K-start.sha` (or `.paths`) | Stage 3 setup 1 | Stage 4.c + Stage 3.5 (per-story Codex; `.sha` as first-story `<prev>` under git, `.paths` as epic-wide path list under non-git) |
| `_bmad-output/.run-state/deferred-work-start.snapshot` | Stage 3 setup 2 | Stage 4.d |
| `_bmad-output/.run-state/cadence-<runId>.txt` | Stage 3 setup 4 | Stage 4.e digest |
| `_bmad-output/.run-state/epic-K-story-<id>-end.sha` | Stage 3.4 | Stage 3.5 + Stage 4.c |
| `_bmad-output/.run-state/epic-K-story-<id>-halt-context.txt` | Stage 3.4 helper `monitor` (on HALT) | Stage 4.e digest |
| `_bmad-output/.run-state/quick-dev-halt-<storyId>.json` | quick-dev (per autonomous-mode-directives #8) | Stage 3.4 helper `monitor` + Stage 4.e digest |
| `_bmad-output/.run-state/epic-K-story-<id>-stall-context.txt` | Stage 3.4 helper `monitor` (on STALL) | Stage 3.C.3 (operator) |
| `_bmad-output/.run-state/epic-K-trace-gate.txt` | Stage 4.a | Stage 4.e digest |
| `_bmad-output/.run-state/epic-K-nfr-gate.txt` | Stage 4.b | Stage 4.e digest |
| `_bmad-output/.run-state/epic-K-nfr-decision.json` | Stage 4.b | Stage 4.e digest |
| `_bmad-output/.run-state/epic-K-codex-skipped.txt` | Stage 4.c (skip path) | Stage 4.e digest |
| `_bmad-output/.run-state/run-digest-<runId>.md` | Stage 4.e | operator |
| `_bmad-output/.run-state/epic-K-retro-signals.txt` | Stage 4.f | Stage 4.g |
| `_bmad-output/test-artifacts/atdd-checklist-<story_key>.md` (canonical, per `bmad-testarch-atdd`'s `outputFile` template + `{project-root}/_bmad/tea/config.yaml`'s `test_artifacts:` setting; `<story_key>` is the full story filename stem, e.g. `K-<id>-<slug>`. Discover via glob `atdd-checklist-K-<id>-*.md`.) | Stage 2.a + 3 (ATDD) | Stage 2.b + 3 (quick-dev) |
| `_bmad-output/implementation-artifacts/epic-K-codex-review.md` | Stage 4.c | Stage 4.e digest |
| `_bmad-output/implementation-artifacts/epic-K-traceability-matrix.md` | Stage 4.a | operator |
| `_bmad-output/implementation-artifacts/epic-K-nfr-assessment.md` | Stage 4.b | operator |
| `_bmad-output/implementation-artifacts/epic-K-deferred-delta.md` | Stage 4.d | Stage 4.e digest |
| `_bmad-output/implementation-artifacts/epic-K-retro-<date>.md` | Stage 4.f | operator |

---

## References

- [references/tracer-readiness-check.md](references/tracer-readiness-check.md) — tracer-readiness gate logic (Stage 2.c)
- [references/autonomous-mode-directives.md](references/autonomous-mode-directives.md) — verbatim directives embedded in Stage 3.1's plain-prompt second message (per the two-message protocol)
- [references/deferred-classifier.md](references/deferred-classifier.md) — authoritative classifier algorithm + marker sets for Stage 4.d; verification fixtures live at `test-fixtures/deferred-classifier/`
- [docs/bmad-auto-design-intent.md](docs/bmad-auto-design-intent.md) — design intent v2 (authoritative)
- [docs/auto-skills-design.md](docs/auto-skills-design.md) — architectural non-negotiables

## Sub-skills invoked

`bmad-spec`, `bmad-sprint-planning`, `bmad-create-story`,
`bmad-check-implementation-readiness`, `bmad-testarch-test-design`,
`bmad-testarch-atdd`, `bmad-quick-dev`, `bmad-testarch-automate`
or `bmad-qa-generate-e2e-tests`, `bmad-code-review`,
`bmad-testarch-trace`, `bmad-testarch-nfr`, `bmad-retrospective`,
`bmad-correct-course`.

Operator-on-demand from Phase 1.e: `bmad-create-architecture`,
`bmad-agent-architect`, `bmad-technical-research`,
`bmad-domain-research`, `bmad-agent-pm`, `bmad-ux`, `bmad-tea`,
`bmad-review-edge-case-hunter`, `/good-ideas`.
