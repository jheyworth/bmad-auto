# Deferred upstream-merge tasks

> Trigger-activated task queue. Each task is deferred until a specific
> upstream BMAD-METHOD merge event fires. **Do not execute these tasks
> preemptively.** When a trigger event fires, this file is consumed by
> a fresh Claude Code session as the authoritative work plan for that
> adoption pass.
>
> **Full upstream-change context + decision rationale lives in
> [`bmad-auto-epic-spec-bundle-adoption.md`](bmad-auto-epic-spec-bundle-adoption.md).**
> This file is the *actionable queue*; that file is the *plan*.

---

## Trigger events

Tasks below are gated on one of these upstream events. Verify the
trigger fired before executing a task (don't trust a screenshot or
hearsay — check the merged PR / closed issue directly).

| Trigger ID | Event | How to verify it fired | Activates |
|---|---|---|---|
| `T-2434` | [BMAD-METHOD issue #2434](https://github.com/bmad-code-org/BMAD-METHOD/issues/2434) merged upstream (Quick Dev recognizes Epic SPEC bundle as authoritative epic context) | (a) issue state is `Closed` AND linked PR is `Merged`; AND (b) Stage 0.11 probe (when it ships via build-tasks T2) reports `epic_spec_bundle_mode=bundle` OR `transitional` | F1, F2, F3, F4 |
| `T-2433` | [BMAD-METHOD issue #2433](https://github.com/bmad-code-org/BMAD-METHOD/issues/2433) merged upstream (Quick Dev "spec" terminology disambiguated from product `SPEC.md`) | (a) issue state is `Closed` AND linked PR is `Merged`; AND (b) the merged PR's final naming choice for Quick Dev's per-run artifact is identified (likely `execution_spec` or `work_order` — confirm in the merged diff) | F5 |

---

## How to activate

A fresh Claude Code session is the executor. Activation protocol:

1. **Verify trigger fired** — check the relevant row in the table
   above. If the trigger has NOT fired, halt; tell the operator.
2. **Read this file** + the linked
   [adoption doc](bmad-auto-epic-spec-bundle-adoption.md)
   for full context.
3. **Identify activated tasks** — every F-series task whose
   `Trigger` column matches the fired trigger.
4. **Execute in dependency order** — respect `BlockedBy` chains.
5. **Update each task's Status** in this file as work progresses
   (`To Do` → `In Progress` → `Done`).
6. **Update Outcome field** when each task completes (files
   modified, deviations from the plan, anything notable).
7. **When all activated tasks are `Done`,** report back to operator
   with a summary + any cross-cutting concerns surfaced during
   execution.

**Operator-in-the-loop.** Where a task names an `OPERATOR GATE`,
pause and wait for the operator's approval before applying changes.

### Activation phrase (paste in a fresh session)

```
The upstream merge for issue #<N> has fired. Open
<bmad-auto>/references/deferred-upstream-tasks.md
and execute the activated tasks.
```

Replace `<N>` with `2434` or `2433` as applicable.

---

## Status legend

| Status | Meaning |
| --- | --- |
| `Deferred` | Default state. Trigger has not fired yet. |
| `Eligible` | Trigger has fired; task is now executable (when `BlockedBy` is clear). |
| `In Progress` | Work in flight, or HALTed pending operator action. |
| `Done` | Completed cleanly. |
| `Cancelled` | Trigger withdrawn / superseded; task no longer relevant. Record reason in Outcome. |

---

## Tasks

### F1 — Stage 3.1 delegation note rewrite (Epic SPEC bundle adoption)

- **Status:** Deferred
- **Trigger:** `T-2434`
- **BlockedBy:** Trigger fired AND `bmad-auto-epic-spec-bundle-adoption.md` T2 (Stage 0.11 probe) is `Done` AND the probe reports `bundle` or `transitional`
- **Goal/Deliverable:** Rewrite Stage 3.1's "Story-file handling
  contract (Phase 3 delegation)" prose in
  `.claude/skills/bmad-auto/SKILL.md` to describe quick-dev's new
  Epic SPEC bundle behavior. Remove the "compile epic context from
  `epics.md`" fallback prose. Add a HALT condition when no Epic SPEC
  bundle exists for epic K.

  When executing:
  - Read the merged upstream PR to confirm the Epic SPEC bundle's
    canonical path/frontmatter shape
  - Update Stage 3.1 prose to match exactly — don't speculate
  - Cross-link to `bmad-spec`'s updated documentation if available
  - Remove the forward-compat caveat that T4 added (it becomes
    obsolete once the adoption lands)

- **Files:** MODIFY `.claude/skills/bmad-auto/SKILL.md` (Stage 3.1
  section + forward-compat caveat removal)
- **OPERATOR GATE:** Yes — show the rewritten Stage 3.1 diff to
  operator before applying. Stage 3.1 is load-bearing for Phase 3
  fanout; mistakes here break the per-story flow.
- **Outcome:** _(fill in on execution)_

---

### F2 — Stage 2.c tracer-readiness gate adds Format C (Epic SPEC bundle)

- **Status:** Deferred
- **Trigger:** `T-2434`
- **BlockedBy:** F1 Done
- **Goal/Deliverable:** Add Format C to the format precedence in
  Stage 2.c (in SKILL.md) and in
  `.claude/skills/bmad-auto/references/tracer-readiness-check.md`.
  Format C = Epic SPEC bundle present + complete (per the merged
  upstream schema). Becomes the *preferred* path when present;
  Format A / A-equivalent fall through.

  Format ordering after F2 lands: **C → A → A-equivalent**.

- **Files:**
  - MODIFY `.claude/skills/bmad-auto/SKILL.md` (Stage 2.c)
  - MODIFY `.claude/skills/bmad-auto/references/tracer-readiness-check.md`
- **OPERATOR GATE:** None (Format C definition is mechanically
  derivable from the merged upstream schema).
- **Outcome:** _(fill in on execution)_

---

### F3 — Directive 6 adds Format C to discovery order

- **Status:** Deferred
- **Trigger:** `T-2434`
- **BlockedBy:** F1 Done
- **Goal/Deliverable:** Update directive 6 ("Re-read architecture +
  scope docs at the start of every story") in
  `.claude/skills/bmad-auto/references/autonomous-mode-directives.md`.
  Add Format C as the new preferred source. Re-rank discovery order:
  **C → A → A-equivalent**.

- **Files:** MODIFY `.claude/skills/bmad-auto/references/autonomous-mode-directives.md`
- **OPERATOR GATE:** None.
- **Outcome:** _(fill in on execution)_

---

### F4 — Phase 1.a input validation adds Epic SPEC bundle row

- **Status:** Deferred
- **Trigger:** `T-2434`
- **BlockedBy:** F1 Done
- **Goal/Deliverable:** Add a new row to Stage 1.a's input
  validation table in `.claude/skills/bmad-auto/SKILL.md`:
  "Epic SPEC bundle for epic K". When the Stage 0.11 probe reports
  `bundle` mode, this artifact is required; HALT if missing.
  Auto-invoke `bmad-spec` for the specific epic via Stage 1.a's
  auto-invocation pattern.

- **Files:** MODIFY `.claude/skills/bmad-auto/SKILL.md` (Stage 1.a
  input validation table + auto-invocation pattern notes)
- **OPERATOR GATE:** None.
- **Outcome:** _(fill in on execution)_

---

### F5 — `/spec/` terminology rename pass (post #2433 merge)

- **Status:** Deferred
- **Trigger:** `T-2433`
- **BlockedBy:** Trigger fired AND final upstream naming choice confirmed
- **Goal/Deliverable:** Mechanical rename pass to align our
  references with Quick Dev's new artifact name (e.g.
  `execution_spec`, `work_order`, or whatever the merged upstream
  PR settled on). Approximately 15–20 sites across SKILL.md +
  `autonomous-mode-directives.md`. Mirrors smoke-fix-3 T5's pattern.

  When executing:
  - Read the merged upstream PR to identify the EXACT new artifact
    name (don't guess)
  - `grep -rn "spec" .claude/skills/bmad-auto/SKILL.md
    .claude/skills/bmad-auto/references/autonomous-mode-directives.md`
    to enumerate sites
  - Apply rename ONLY where the term refers to Quick Dev's per-run
    artifact (do NOT rename references to the project `SPEC.md`,
    `bmad-spec`, or our skill's `SKILL.md` files)
  - Re-verify the directive 1 scope-limit prose (added by T3 in
    the adoption doc) still reads coherently after the rename

- **Files:**
  - MODIFY `.claude/skills/bmad-auto/SKILL.md` (multiple sites)
  - MODIFY `.claude/skills/bmad-auto/references/autonomous-mode-directives.md`
  - MAYBE MODIFY `.claude/skills/bmad-auto/references/tracer-readiness-check.md`
    (if it references Quick Dev's spec by name)
- **OPERATOR GATE:** Mid-rename review — show operator a sample of
  edits before applying the full pass. Pattern is mechanical but
  the disambiguation context matters (don't break the project-`SPEC.md`
  vs Quick-Dev-execution-spec distinction we just established).
- **Outcome:** _(fill in on execution)_

---

## What to do if a trigger is withdrawn

If either upstream issue is **closed without merge** (Alex withdraws,
the design is superseded, etc.):

1. Mark the affected tasks `Cancelled`
2. Record reason in each task's Outcome field (link to the
   closed/withdrawn issue + any successor discussion)
3. Update the adoption doc
   ([`bmad-auto-epic-spec-bundle-adoption.md`](bmad-auto-epic-spec-bundle-adoption.md))
   to reflect the new state
4. If a *successor* issue emerges (e.g. Alex re-files with a different
   approach), open a peer adoption doc; cross-link from here

## What to do if a trigger fires but the merged shape is unexpected

If a trigger fires but the merged upstream PR differs significantly
from the issue description (e.g. final design abandons the Epic SPEC
bundle concept in favor of something else):

1. Pause execution of activated tasks
2. Surface the deviation to the operator
3. Update the trigger event description in this file to match the
   merged reality
4. Revise task descriptions before resuming — don't blindly execute
   tasks written against a pre-merge design that diverged

---

## Cross-references

- Full upstream-change context + decision rationale + do-now task
  details (T1–T4):
  [`bmad-auto-epic-spec-bundle-adoption.md`](bmad-auto-epic-spec-bundle-adoption.md)
- BMAD-METHOD issue tracking:
  - [#2434 — Epic SPEC bundle](https://github.com/bmad-code-org/BMAD-METHOD/issues/2434)
  - [#2433 — execution-spec disambiguation](https://github.com/bmad-code-org/BMAD-METHOD/issues/2433)
- Closest precedent for the "task list as canonical tracker"
  convention this file uses:
  `bmad-auto-v5-smoke-fix-3.md`
