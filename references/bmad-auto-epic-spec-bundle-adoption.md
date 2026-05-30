# Forward-compat: Epic SPEC bundle adoption + execution-spec disambiguation

> Tracks BMAD-METHOD issues [#2434](https://github.com/bmad-code-org/BMAD-METHOD/issues/2434)
> + [#2433](https://github.com/bmad-code-org/BMAD-METHOD/issues/2433) (Alex
> Verkhovsky) that affect `/bmad-auto` when they ship upstream. Do-now
> tasks (T1–T4) minimize risk that future upstream merges break our
> autonomous flow; deferred tasks (F1–F5) capture the integration plan
> but wait for upstream to ship before landing.
>
> **Cold-session start here.** Read the "Status snapshot" + the linked
> issues before executing any task.

---

## Status snapshot (cold-session handover)

### Why this file exists

Two open issues in BMAD-METHOD (filed 2026-05-27 by Alex Verkhovsky,
the originator of the `/bmad-auto` pipeline design) touch behavior our
skill currently depends on:

| Issue | Title | Status | Direct impact on `/bmad-auto` |
|---|---|---|---|
| [#2434](https://github.com/bmad-code-org/BMAD-METHOD/issues/2434) | Quick Dev epic context generation should recognize BMad SPEC epic bundles | OPEN, not merged | Stage 3.1 delegation note + directive 6 discovery order + Phase 1.a input validation + Stage 2.c tracer-readiness gate all rely on quick-dev's `compile-epic-context` path that is being deprecated |
| [#2433](https://github.com/bmad-code-org/BMAD-METHOD/issues/2433) | Quick Dev should distinguish execution specs from product SPEC.md artifacts | OPEN, not merged | Naming-overlap risk that an autonomous session reads a project `SPEC.md` with `Status: implementation-ready` and short-circuits Quick Dev's approval checkpoint; affects directive 1's wording in particular |

The issues are not yet merged. The do-now items in this doc preempt
the structural risks without speculating on exact upstream syntax;
the deferred items capture the adoption plan for the day upstream
ships.

### What #2434 changes upstream

Quick Dev's current behavior:
1. Receives a `--story-id` / story name
2. If only a skeleton exists in `epics.md`, compiles its own
   `epic-<N>-context.md` from raw planning artifacts
3. Generates the per-story execution spec
4. Implements

Alex's intended behavior:
1. Resolve epic + story
2. **Find the Epic SPEC bundle** (a structured per-epic artifact
   authored by `bmad-spec`, distinct from the project SPEC)
3. Load the Epic SPEC bundle + companions as authoritative context
4. Generate per-story execution spec
5. **HALT for approval**
6. Only then implement
7. **If no Epic SPEC bundle exists → HALT and ask user to run Epic
   Spec for that epic first** (no more synthesis from raw artifacts)

The hierarchy Alex names:
- Product/project SPEC = broad product contract
- **Epic SPEC bundle = authoritative epic context for implementation sessions**
- Quick Dev execution spec/work order = per-story implementation plan

The shape of the Epic SPEC bundle path/frontmatter is not yet
specified upstream (no merged PR yet); the probe in T2 detects
presence-by-marker rather than relying on an exact schema.

### What #2433 changes upstream

Quick Dev's "spec" terminology is being disambiguated:
- Quick Dev runtime variable `spec_file` → likely `execution_spec_file`
  or `work_order_file`
- Quick Dev generated files `spec-*.md` → likely
  `execution-spec-*.md` or `work-order-*.md`
- Quick Dev template `spec-template.md` → likely
  `execution-spec-template.md`
- BMad canonical artifact `SPEC.md` stays as-is (`bmad-spec` owns the name)

A hard invariant Alex proposes:

> Do not edit source files from planning artifacts alone. A BMad
> project/epic `SPEC.md` with `Status: implementation-ready` is not
> approval to implement in Quick Dev. Only an approved Quick Dev
> execution spec/work order with recognized frontmatter status
> unlocks implementation.

That invariant is what protects against an autonomous agent reading
the project `SPEC.md`'s `Status: implementation-ready` and skipping
Quick Dev's Step 2 checkpoint. Our `/bmad-auto` autonomous mode is
exactly the failure-mode surface this guards.

### What's affected in our skill (snapshot at 2026-05-27)

| File | Section | Issue | Affected text (current) |
|---|---|---|---|
| `.claude/skills/bmad-auto/SKILL.md` | Stage 3.1 "Story-file handling contract (Phase 3 delegation)" | #2434 | "if only a skeleton exists in `epics.md`, [quick-dev] compiles epic context (`epic-K-context.md` cached in implementation-artifacts) and generates the spec in step-02" |
| `.claude/skills/bmad-auto/SKILL.md` | Stage 1.a input validation table | #2434 | Currently checks project SPEC + `epics.md` + per-story files; doesn't check for Epic SPEC bundle |
| `.claude/skills/bmad-auto/SKILL.md` | Stage 2.c tracer-readiness gate (Format A / A-equivalent) | #2434 | Two-way format precedence will need a third entry (Format C — Epic SPEC bundle as authoritative) |
| `.claude/skills/bmad-auto/SKILL.md` | Stage 0 Preflight | #2434 | No probe for Epic SPEC bundle support; mirrors the 0.8 architecture-spine probe pattern |
| `.claude/skills/bmad-auto/references/autonomous-mode-directives.md` | Directive 1 (CHECKPOINT 1) | #2433 | "Quick-dev's Step 2 spec-approval gate" — uses "spec" ambiguously; doesn't explicitly scope-limit to Quick Dev's INTERNAL execution spec |
| `.claude/skills/bmad-auto/references/autonomous-mode-directives.md` | Directive 6 (Re-read architecture + scope docs) | #2434 | Lists (a) Format A — `epic-K-micro-architecture.md`; (b) Format A-equivalent — `architecture.md` + `SPEC.md`. Needs Format C (Epic SPEC bundle). |
| `.claude/skills/bmad-auto/references/tracer-readiness-check.md` | Format precedence | #2434 | Mirrors SKILL.md Stage 2.c; same gap |
| `.claude/skills/bmad-auto/SKILL.md` | Various "spec" prose | #2433 | Mechanical rename pass post-upstream-merge; ~15-20 sites |

### Risks if we do nothing now

- **When #2434 lands**, the next `/bmad-auto` run on any project will
  HALT at Phase 3 because Quick Dev refuses to do
  `compile-epic-context`. We'd need an emergency adoption pass.
- **When #2433's hard invariant lands**, autonomous-mode runs might
  fail Quick Dev's tightened checkpoint guards because directive 1
  doesn't distinguish layers clearly.
- Today (pre-merge), neither risk is active. The do-now items in this
  doc are insurance, not emergencies.

---

## Source-of-truth references

**Before executing any task, read:**

1. [BMAD-METHOD issue #2434](https://github.com/bmad-code-org/BMAD-METHOD/issues/2434) —
   Epic SPEC bundle as authoritative epic context.
2. [BMAD-METHOD issue #2433](https://github.com/bmad-code-org/BMAD-METHOD/issues/2433) —
   execution-spec vs product-SPEC disambiguation.
3. [`SKILL.md`](../SKILL.md) —
   our orchestrator skill. Stage 0.8 (probe pattern), Stage 1.a
   (input validation), Stage 2.c (tracer-readiness gate), Stage 3.1
   (delegation note) all need awareness.
4. [`autonomous-mode-directives.md`](autonomous-mode-directives.md) —
   directive 1 (the most important do-now edit) and directive 6
   (deferred until upstream ships).
5. [`tracer-readiness-check.md`](tracer-readiness-check.md) —
   F2's target.
6. `bmad-auto-v5-smoke-fix-3.md` —
   most recent precedent for "task list as canonical tracker"
   convention.

---

## How to use this file

```
continue <bmad-auto>/references/bmad-auto-epic-spec-bundle-adoption.md
```

Paste that one line as the first message in a fresh Claude Code
session. The session reads this file, finds the next `To Do` task with
all `BlockedBy` items `Done`, and proceeds — operator-in-the-loop, not
headless.

---

## Status legend

| Status | Meaning |
| --- | --- |
| `To Do` | Not started. Eligible when every `BlockedBy` is `Done`. |
| `In Progress` | Work in flight, or HALTed pending operator action. |
| `Done` | Completed cleanly. |
| `Blocked` | Surfaced an issue that halts progress; capture in Outcome. |
| `Deferred` | Waiting on upstream merge; do not execute until trigger event named in the task. |

---

## Do-now tasks (T1–T4) — execute before upstream merges

> **Reclassification (2026-05-30).** After tracing quick-dev's installed
> step files, the #2433 risk was recalibrated to *narrow insurance*:
> quick-dev's `step-01-clarify-and-route.md` only resumes a file as a spec
> when it has recognized `status` **frontmatter** (`draft` / `ready-for-dev`
> / `in-progress` / `in-review` / `done`) — arbitrary `Status:
> implementation-ready` body text does NOT match, so the issue's headline
> collapse path is largely unreachable. Residual exposure is narrow (a
> bmad-spec `SPEC.md` carrying colliding `status` frontmatter), and both
> #2433 / #2434 remain OPEN/unmerged. Re-triage outcome: **T3 applied**
> (cheap, present-relevant judgment-hardening). **T2 + T4 reclassified `To
> Do` → `Deferred`** — they are speculative forward-compat (a permanent
> preflight probe + a doc caveat) for unshipped upstream, so they
> trigger-activate alongside the F-series rather than pre-build, consistent
> with this repo's lean-orchestrator / wait-for-trigger discipline. T1
> remains Done.

### T1 — Author this tracking doc

- **Status:** Done
- **BlockedBy:** —
- **Goal/Deliverable:** This file. Captures the upstream changes,
  what's affected in our skill, and the integration plan.
- **Files:** NEW `skills/bmad-auto/references/bmad-auto-epic-spec-bundle-adoption.md`
- **Outcome:** Authored 2026-05-27 by the orchestrator session that
  reviewed issues #2434 + #2433. Approved by the operator as part of the
  forward-compat work surfaced post-smoke-fix-3 close. Moved 2026-05-28
  from `` to `skills/bmad-auto/references/` to
  co-locate with its trigger-list sibling and simplify cross-links.

---

### T2 — Add Stage 0 Preflight probe for Epic SPEC bundle support

- **Status:** Deferred (reclassified 2026-05-30 — see note under the section header; trigger-activate with the F-series when #2434 moves)
- **BlockedBy:** T1
- **Goal/Deliverable:** Add an 11th preflight probe step to SKILL.md's
  Stage 0 mirroring the existing Stage 0.8 architecture-spine probe.
  The probe detects whether `bmad-spec` / `bmad-quick-dev` source has
  Epic SPEC bundle awareness; records the signal to a sidecar; Stage
  1.a + Stage 3.1 consume the signal in future tasks (F1, F4).

  **Probe logic (defensive — no speculation on exact upstream syntax):**

  ```sh
  # Probe 1: does bmad-spec mention "epic" handling beyond the
  # project-spec scope? (e.g. epic-level SPEC generation.)
  grep -l -i -E '\b(epic[ -]spec|epic[ -]bundle|per[ -]epic[ -]spec)\b' \
    .claude/skills/bmad-spec/SKILL.md \
    .claude/skills/bmad-spec/customize.toml \
    2>/dev/null

  # Probe 2: does bmad-quick-dev still have a compile-epic-context
  # step file, or has it been removed in favor of Epic SPEC bundle reads?
  test -f .claude/skills/bmad-quick-dev/steps-c/*compile-epic-context* \
    && echo "compile-epic-context still present" \
    || echo "compile-epic-context appears removed"
  ```

  Set `epic_spec_bundle_mode` to one of:
  - `legacy` — `bmad-spec` has no epic-level markers AND
    `compile-epic-context` step file still exists (today's state)
  - `bundle` — `bmad-spec` has epic-level markers AND
    `compile-epic-context` removed (post-#2434 state)
  - `transitional` — mixed signals (one marker but not the other);
    surface to operator for triage

  Persist to `_bmad-output/.run-state/epic-spec-bundle-mode.txt`. Phase
  1.a + Stage 3.1 consume the value via future F-series tasks.

- **Files:**
  - MODIFY `.claude/skills/bmad-auto/SKILL.md` — add Stage 0.11 probe
    section after Stage 0.10 (run-state dir init)
  - MAYBE NEW `_bmad-output/.run-state/epic-spec-bundle-mode.txt`
    (created at probe runtime)

- **Acceptance criteria:**
  - SKILL.md Stage 0 has an 11th probe step matching the 0.8 pattern
    (probe → record signal → consumer note)
  - Probe defaults to `legacy` when run today (verify by running the
    probe against the current `.claude/skills/bmad-spec/`)
  - Probe surfaces transitional state to operator (HALT or warn,
    depending on operator preference — recommend warn-only since the
    probe is forward-compat only)
  - Sidecar file index (SKILL.md table) has a new row for
    `epic-spec-bundle-mode.txt` with producer Stage 0.11 + consumer
    "Stage 1.a + Stage 3.1 (future F-series adoption)"

- **OPERATOR GATE:** None for probe authoring. T2 is structurally
  passive (records signal, doesn't change behavior).

- **Picker notes:**
  - Don't add Stage 1.a / Stage 3.1 consumer logic in T2. That belongs
    to F1 + F4 when upstream is closer. T2 just plants the signal.
  - The probe is conservative: it defaults to `legacy` and current
    behavior continues. The day upstream ships, the probe flips to
    `bundle` and operator sees the signal in Stage 0 output —
    triggering the F-series adoption.
  - Probe should NOT halt the preflight on `transitional` state. Warn
    only. Rationale: the operator should be able to test things even
    in a mixed-upstream state.

- **Session boundary suggestion:** Continue with T3 + T4 in the same
  session. Each is small (~5–10 line prose edit).

- **Outcome:** _(fill in when Done)_

---

### T3 — Tighten directive 1 in `autonomous-mode-directives.md`

- **Status:** Done
- **BlockedBy:** T1
- **Goal/Deliverable:** Update directive 1 to scope-limit the
  auto-approve behavior to Quick Dev's INTERNAL execution-spec
  checkpoint, and explicitly reject the failure mode #2433 names
  (interpreting upstream `SPEC.md` `Status: implementation-ready` as
  authorization to bypass Quick Dev).

  **Concrete edit:**

  **OLD directive 1:**
  > 1. **CHECKPOINT 1 — default `[A] Approve`.** Quick-dev's Step 2
  > spec-approval gate auto-approves unless the spec is **obviously
  > broken**. Obviously broken means: missing one of the required
  > spec sections (Intent, Boundaries & Constraints, I/O & Edge-Case
  > Matrix, Code Map, Tasks & Acceptance, Verification), acceptance
  > criteria that directly contradict each other or the stated
  > Intent, or scope that is clearly outside the named story (e.g.
  > references an epic that isn't K). Anything else is judgment-call
  > material and gets `[A]`. Rationale: in autonomous mode no
  > operator is available to type `[A]`, but blanket-approving
  > structurally broken specs corrupts the run — judgement still
  > applies, the default is just inverted.

  **NEW directive 1:**
  > 1. **CHECKPOINT 1 — default `[A] Approve` (execution-spec scope only).**
  > Quick-dev's Step 2 **execution-spec** approval gate auto-approves
  > unless the execution spec is **obviously broken**. Obviously
  > broken means: missing one of the required spec sections (Intent,
  > Boundaries & Constraints, I/O & Edge-Case Matrix, Code Map,
  > Tasks & Acceptance, Verification), acceptance criteria that
  > directly contradict each other or the stated Intent, or scope
  > that is clearly outside the named story (e.g. references an
  > epic that isn't K). Anything else is judgment-call material and
  > gets `[A]`. Rationale: in autonomous mode no operator is
  > available to type `[A]`, but blanket-approving structurally
  > broken specs corrupts the run — judgement still applies, the
  > default is just inverted.
  >
  > **Scope of this directive (do not collapse):** This approval
  > applies ONLY to Quick Dev's per-story execution spec (the work
  > order Quick Dev generates at Step 2). It is NEVER authorization
  > to bypass Quick Dev's flow and edit source from upstream
  > planning artifacts alone — even if the project `SPEC.md`, an
  > epic `SPEC.md`, or the Epic SPEC bundle declares `Status:
  > implementation-ready`. The execution spec is a Quick Dev
  > artifact distinct from any upstream `SPEC.md`; only its
  > approval (or one-shot route equivalent) unlocks source edits.
  > See [BMAD-METHOD #2433](https://github.com/bmad-code-org/BMAD-METHOD/issues/2433)
  > for the structural distinction.

- **Files:**
  - MODIFY `.claude/skills/bmad-auto/references/autonomous-mode-directives.md`

- **Acceptance criteria:**
  - Directive 1's auto-approve scope is explicitly limited to Quick
    Dev's execution spec
  - A new explicit "Scope of this directive (do not collapse)" block
    rejects the failure mode #2433 names
  - The link to issue #2433 grounds the scoping rationale in the
    upstream conversation
  - No regression: existing tests that consume autonomous-mode-
    directives.md still pass (the suppression-set composition checks
    in `test_halt_check_directive_echo.py` and peers are concerned
    with verbatim text matching, not directive semantics — a prose
    extension should not break them, but verify)

- **OPERATOR GATE:** None. T3 is a focused prose edit; operator can
  review the diff post-application.

- **Picker notes:**
  - Don't rename "spec" → "execution spec" throughout the directive
    yet. That's the deferred F5 task. T3 is targeted at directive 1
    only because it's the load-bearing autonomous-mode safety guard.
  - The new "Scope" block must be readable on its own — a future
    autonomous agent reading directive 1 should be able to
    distinguish "approve the execution spec" from "the upstream
    SPEC.md is authorization" without cross-referencing.

- **Session boundary suggestion:** Continue with T4 in same session.

- **Outcome:** Applied 2026-05-30. Directive 1 retitled "(execution-spec
  scope only)" with an appended "Scope of this directive (do not collapse)"
  block: scopes auto-approval to Quick Dev's per-story execution spec and
  explicitly rejects an upstream project/epic `SPEC.md` (or Epic SPEC
  bundle) declaring `Status: implementation-ready` — or carrying `status`
  frontmatter colliding with `ready-for-dev` / `in-progress` — as
  authorization to edit source. Grounds the rationale in #2433.
  Directive-echo + halt-check suppression tests pass 26/26; full hermetic
  suite green. The lone full-run failure (`test_e2e_phase1_fail`, a
  live-`claude` e2e needing API infra) is unrelated — it exercises Phase
  1.e findings production, not the directives file; the only test that
  consumes the edited file (`test_spawn_two_message_split.py`) passed.
  **Caveat:** this is soft/judgment-level protection. The narrow mechanical
  collapse path is quick-dev's `step-01` routing (early-exit to
  `step-03-implement` on a recognized `status` frontmatter value), which
  fires *before* directive 1 — T3 patches the spawned agent's judgment, not
  a hard interlock. **Follow-up applied same day (T3+):** directive 1's scope
  block was extended with an *affirmative pre-resume verification* — before any
  early-exit to implementation the agent must positively confirm the file is
  Quick Dev's own execution spec (lives in `implementation-artifacts/`, matches
  the execution-spec template shape, was produced by Quick Dev's Step 2 for this
  story), else route through Step 2 + this gate; a recognized `status` value
  alone is explicitly declared insufficient provenance. This is the strongest
  agent-level interlock available without forking quick-dev. A *true* mechanical
  interlock still requires the upstream #2433 fix to quick-dev's step-01 routing.
  Tests re-run after this addition: 32/32 (directive-echo + 1..8 numbering guard
  + halt-check) pass; directive count still parses as 8.

---

### T4 — Add forward-compat caveat to SKILL.md Stage 3.1's delegation note

- **Status:** To Do
- **BlockedBy:** T1
- **Goal/Deliverable:** Add a short forward-compat caveat to Stage
  3.1's "Story-file handling contract (Phase 3 delegation)" note so
  future readers know quick-dev's `compile-epic-context` path is
  being deprecated. The caveat doesn't change behavior; it documents
  the upstream issue and points at this adoption doc.

  **Concrete edit:**

  At the end of Stage 3.1's "Story-file handling contract" paragraph,
  ADD a new paragraph:

  > **Forward-compat (BMAD-METHOD issue
  > [#2434](https://github.com/bmad-code-org/BMAD-METHOD/issues/2434)
  > — pending upstream):** quick-dev's `compile-epic-context` path
  > (the "compile from `epics.md`" fallback above) is being
  > deprecated in favor of an Epic SPEC bundle authored by
  > `bmad-spec`. When that change ships, quick-dev will HALT
  > instead of synthesizing epic context. `/bmad-auto`'s adoption
  > plan is captured in
  > [`references/bmad-auto-epic-spec-bundle-adoption.md`](bmad-auto-epic-spec-bundle-adoption.md).
  > The Stage 0.11 probe (`epic-spec-bundle-mode.txt`) detects when
  > the upstream change has landed and surfaces the signal here.

- **Files:**
  - MODIFY `.claude/skills/bmad-auto/SKILL.md` (Stage 3.1 section)

- **Acceptance criteria:**
  - Caveat paragraph appended to Stage 3.1 with the issue link + the
    adoption doc link + the probe sidecar reference
  - No other SKILL.md text changes (this is a conservative add, not
    a rewrite — rewrite is F1's job when upstream ships)

- **OPERATOR GATE:** None.

- **Picker notes:**
  - Don't preemptively rewrite the "compile epic context" sentence.
    The current behavior is still correct today; the caveat just
    flags the future change.

- **Session boundary suggestion:** Close T2 + T3 + T4 in the same
  session — they're all small and tightly related.

- **Outcome:** _(fill in when Done)_

---

## Deferred tasks (F1–F5) — wait until upstream ships

These are the integration changes that land *when* one or both of
#2434 / #2433 are merged upstream. They are **not** to be executed
preemptively. Each task's `BlockedBy` includes the upstream merge
event as a precondition.

> **Actionable on-disk queue lives at
> [`deferred-upstream-tasks.md`](deferred-upstream-tasks.md).**
> That file is the trigger-activated work queue (paste its activation
> phrase in a fresh session when an upstream merge fires); the summary
> below is the *plan*. Both files should agree on F-series shape — if
> they drift, the trigger-list is the source of truth for execution
> details, this file is the source of truth for rationale.

### F1 — Stage 3.1 delegation note rewrite (Epic SPEC bundle adoption)

- **Status:** Deferred
- **BlockedBy:** #2434 merged upstream; T2's probe reports `bundle`
  or `transitional` state
- **Goal/Deliverable:** Rewrite Stage 3.1's "Story-file handling
  contract" to describe quick-dev's new Epic SPEC bundle behavior.
  Remove the "compile epic context from epics.md" fallback prose.
  Add a HALT condition when no Epic SPEC bundle exists for epic K.

  **Trigger event:** Probe in T2 flips from `legacy` to `bundle`
  (verified by running `bash` snippet against the upstream-updated
  `.claude/skills/bmad-spec/`).

- **Files:** MODIFY `.claude/skills/bmad-auto/SKILL.md` Stage 3.1
- **Outcome:** _(fill in when upstream ships + F1 executes)_

### F2 — Stage 2.c tracer-readiness gate adds Format C (Epic SPEC bundle)

- **Status:** Deferred
- **BlockedBy:** #2434 merged; F1 done
- **Goal/Deliverable:** Add Format C to the two-way precedence in
  Stage 2.c + the tracer-readiness-check.md reference. Format C =
  Epic SPEC bundle present + complete. Becomes the preferred path
  when present; Format A / A-equivalent fall through.
- **Files:**
  - MODIFY `.claude/skills/bmad-auto/SKILL.md` Stage 2.c
  - MODIFY `.claude/skills/bmad-auto/references/tracer-readiness-check.md`
- **Outcome:** _(fill in when F2 executes)_

### F3 — Directive 6 adds Format C to discovery order

- **Status:** Deferred
- **BlockedBy:** #2434 merged; F1 done
- **Goal/Deliverable:** Update directive 6 ("Re-read architecture +
  scope docs at the start of every story") to add Format C — Epic
  SPEC bundle as the new preferred source. Re-rank: C → A → A-equivalent.
- **Files:** MODIFY `.claude/skills/bmad-auto/references/autonomous-mode-directives.md`
- **Outcome:** _(fill in when F3 executes)_

### F4 — Phase 1.a input validation adds Epic SPEC bundle row

- **Status:** Deferred
- **BlockedBy:** #2434 merged; F1 done
- **Goal/Deliverable:** Add a new row to Stage 1.a's input validation
  table: "Epic SPEC bundle for epic K" — required when the upstream
  feature is present (per T2's probe). HALT if missing; auto-invoke
  `bmad-spec` for the specific epic via Stage 1.a's auto-invocation
  pattern.
- **Files:** MODIFY `.claude/skills/bmad-auto/SKILL.md` Stage 1.a
- **Outcome:** _(fill in when F4 executes)_

### F5 — SKILL.md + directives.md "spec" terminology pass (post #2433 merge)

- **Status:** Deferred
- **BlockedBy:** #2433 merged upstream with final naming choice
  confirmed
- **Goal/Deliverable:** Mechanical rename pass to use Quick Dev's new
  artifact name (e.g. `execution_spec` or `work_order` — depends on
  final upstream choice). ~15-20 sites across SKILL.md +
  directives.md. Mirrors smoke-fix-3 T5's pattern.
- **Files:**
  - MODIFY `.claude/skills/bmad-auto/SKILL.md` (multiple sites)
  - MODIFY `.claude/skills/bmad-auto/references/autonomous-mode-directives.md`
- **Outcome:** _(fill in when F5 executes)_

---

## Closing checklist (after T4 completes)

When T1–T4 are Done:

- [ ] SKILL.md has an 11th Stage 0 probe step recording
      `epic-spec-bundle-mode.txt`
- [ ] Sidecar file index includes `epic-spec-bundle-mode.txt` row
- [ ] Directive 1 in autonomous-mode-directives.md has the scope-
      limited language + link to issue #2433
- [ ] Stage 3.1 has the forward-compat caveat with links to issue
      #2434 + this adoption doc
- [ ] No existing tests broken by the prose-only edits (run the
      full pytest suite)
- [ ] Watch GitHub for #2434 / #2433 merges; trigger F-series when
      they land

---

## Failure modes / what to do if blocked

If any task enters `Blocked`:

1. Record the blocking issue in the task's Outcome field
2. Surface to the operator with: which task, what the block is, what
   info is needed to unblock
3. Do NOT execute F-series tasks preemptively — they're explicitly
   deferred until upstream ships

If the upstream issues are CLOSED without merge (i.e. Alex withdraws
or rewrites them):
- T1–T4's forward-compat language is still defensible — the
  scope-limit on directive 1 is independently valuable, and the
  Stage 3.1 caveat is a docs improvement either way
- F1–F5 should be removed from this doc (mark as `Cancelled` with a
  link to the closed/withdrawn issue)

If a different upstream issue lands that affects similar surface area
(e.g. a #2435 about per-story execution-spec frontmatter schema):
- Open a peer adoption doc; cross-link
- Don't accumulate unrelated forward-compat work in this file
