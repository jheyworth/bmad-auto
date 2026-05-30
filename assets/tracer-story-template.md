---
title: 'Epic <K> tracer: <epic title>'
type: 'feature'
created: '<YYYY-MM-DD>'
status: 'draft'
context: []
---

<!--
  This is the TRACER STORY for epic <K>. A tracer is the first story of an
  epic, implemented end-to-end so every subsequent story has a concrete
  pattern to follow. Pull architectural unknowns LEFT — the tracer is where
  unknowns become concrete code.

  Workflow expectation:
    1. Operator (you) fills in the placeholders below — especially the
       narrative, acceptance criteria, and any I/O scenarios.
    2. Operator runs `/bmad-quick-dev` against THIS FILE to implement it.
       Quick-dev will route based on `status: draft` and walk you through
       planning, implementation, and review.
    3. While implementing, also produce the tracer-readiness contract:
         - Format A (per-epic micro-docs — primary):
             _bmad-output/implementation-artifacts/epic-<K>-micro-prd.md
             _bmad-output/implementation-artifacts/epic-<K>-micro-architecture.md
           Each with the five required sections per
           skills/bmad-auto/references/tracer-readiness-check.md.
         - Format A-equivalent (whole-project short-circuit — acceptable
           fallback for small / single-epic projects that don't produce
           per-epic distillation):
             _bmad-output/planning-artifacts/architecture.md
             plus the project SPEC / PRD
           These supply the same five PRD-equivalent and architecture-
           equivalent section coverage at the whole-project level.
       Either form satisfies the contract. The readiness check prefers
       Format A when the per-epic micro-doc markers are present and falls
       through to Format A-equivalent otherwise.
    4. When story <K>.1 is `done` AND the contract artifacts (Format A or
       Format A-equivalent) exist with all required sections populated, run
       `/bmad-auto --verify --epics <K>` to confirm tracer-readiness, then
       `/bmad-auto --dev --epics <K>` to launch autonomous execution of the
       remaining stories in epic <K>.

  Remove these HTML comments and any unused sections before submitting.

  Target: 900–1300 tokens. Above 1600 risks context rot in implementation.
-->

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

<!-- The narrative. What's broken or missing, why it matters, the high-level
     approach. The "what", not the "how". -->

**Problem:** <one to two sentences describing the user-facing problem this
epic exists to solve, framed at the tracer's slice.>

**Approach:** <one to two sentences on the high-level approach — the slice
the tracer will demonstrate end-to-end.>

**Story narrative:**

- **As a** <persona>
- **I want** <capability the tracer demonstrates>
- **So that** <outcome / value>

## Boundaries & Constraints

<!-- Always = invariant rules. Ask First = human-gated decisions. Never =
     out of scope and forbidden approaches. -->

**Always:** <invariant rules the implementation must respect — e.g. data
formats, naming conventions, public-interface stability.>

**Ask First:** <decisions that require human approval if they come up — e.g.
schema changes, new dependencies, API contract changes.>

**Never:** <non-goals and forbidden approaches — e.g. "do not introduce a
new framework", "do not modify other epics' code".>

## I/O & Edge-Case Matrix

<!-- If no meaningful I/O scenarios exist for the tracer, DELETE THIS
     ENTIRE SECTION. Do not write "N/A" or "None". -->

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | <input> | <outcome> | N/A |
| ERROR_CASE | <input> | <outcome> | <error handling> |

</frozen-after-approval>

## Code Map

<!-- Agent-populated during planning (quick-dev step-02). Annotated paths
     prevent blind codebase searching. Leave the placeholders below in
     place — quick-dev will replace them. -->

- `<file>` -- <role or relevance>
- `<file>` -- <role or relevance>

## Tasks & Acceptance

<!-- Tasks: backtick-quoted file path -- action -- rationale. Prefer one task
     per file; group tightly-coupled changes when splitting would be
     artificial. -->
<!-- AC covers system-level behaviors not captured by the I/O Matrix. Use
     Given/When/Then form. Do not duplicate I/O scenarios here. -->

**Execution:**
- [ ] `<file>` -- <action> -- <rationale>
- [ ] `<file>` -- <action> -- <rationale>

**Acceptance Criteria:**
- Given <precondition>, when <action>, then <expected result>.
- Given <precondition>, when <action>, then <expected result>.

**Tracer-specific acceptance criteria (REQUIRED — do not delete):**
- Given the tracer story is implemented, when an operator runs
  `/bmad-auto --verify --epics <K>`, then the tracer-readiness check
  defined in `skills/bmad-auto/references/tracer-readiness-check.md`
  passes against either Format A or Format A-equivalent (see header
  comment).
- Given the tracer story is implemented, when sprint-status.yaml is
  inspected, then the story-1 key for epic <K> is set to `done`.

## Spec Change Log

<!-- Append-only. Populated by quick-dev step-04 during review loops. Do not
     modify or delete existing entries. Empty until the first bad_spec
     loopback. -->

## Design Notes

<!-- If the approach is straightforward, DELETE THIS ENTIRE SECTION. Do not
     write "N/A" or "None". -->
<!-- Design rationale and golden examples only when non-obvious. Keep
     examples to 5–10 lines. -->

<design rationale, golden examples, key architectural decisions that the
tracer is meant to demonstrate concretely so the remaining stories of epic
<K> can follow the pattern.>

## Verification

<!-- If no build, test, or lint commands apply, DELETE THIS ENTIRE SECTION.
     Do not write "N/A" or "None". -->

**Commands:**
- `<command>` -- expected: <success criteria>

**Manual checks (if no CLI):**
- <what to inspect and the expected state>

## Required tracer deliverables (do not delete — owned by bmad-auto)

Beyond the implementation itself, the tracer story is responsible for
producing the **tracer-readiness contract** that downstream stories of epic
<K> consume. One of the following two artifact sets must exist and be
populated before `/bmad-auto --verify --epics <K>` will pass:

### Format A — per-epic micro-docs (primary)

- `_bmad-output/implementation-artifacts/epic-<K>-micro-prd.md` with the
  sections: `## Intent`, `## Scope`, `## Non-goals`,
  `## User-facing surface`, `## Open questions` — each non-empty.
- `_bmad-output/implementation-artifacts/epic-<K>-micro-architecture.md`
  with the sections: `## Architecture decisions`, `## Patterns established`,
  `## Conventions`, `## Integration points`, `## Gotchas / footguns` —
  each non-empty.

### Format A-equivalent — whole-project short-circuit (fallback)

For small / single-epic projects that don't produce per-epic distillation,
the whole-project planning artifacts substitute for the per-epic micro-docs:

- `_bmad-output/planning-artifacts/architecture.md` covering the same
  architecture-equivalent sections (`## Architecture decisions`,
  `## Patterns established`, `## Conventions`, `## Integration points`,
  `## Gotchas / footguns`) at the whole-project level.
- The project SPEC / PRD covering the same PRD-equivalent sections
  (`## Intent`, `## Scope`, `## Non-goals`, `## User-facing surface`,
  `## Open questions`) at the whole-project level.

The readiness check prefers Format A when the per-epic micro-doc markers
are present and falls through to Format A-equivalent otherwise. Pick
whichever fits the project — per-epic micro-docs for multi-epic projects
where each epic warrants its own distillation, whole-project artifacts
for smaller single-epic projects.

Authoring these distillations is part of the tracer story, not a follow-up
chore. They're the artifacts that let subsequent stories run autonomously.
