---
spec_id: spec-e2e
title: bmad-auto e2e fixture
status: complete
ux_surface: none
companions: []
assumptions: []
open_questions: []
---

# SPEC — bmad-auto e2e fixture

## Capabilities

### CAP-1 — Tracer file write

Story `99-1-tracer` must create `e2e-tracer.txt` in the repo root with
the literal content `tracer-story-99-1\n`.

**Acceptance criteria:**

- File exists at `./e2e-tracer.txt`
- Content is exactly `tracer-story-99-1\n` (no trailing whitespace
  variation)

### CAP-2 — Fanout file write

Story `99-2-fanout` must create `e2e-fanout.txt` in the repo root with
the literal content `fanout-story-99-2\n`.

**Acceptance criteria:**

- File exists at `./e2e-fanout.txt`
- Content is exactly `fanout-story-99-2\n`

## Non-functional requirements

None. This fixture is deliberately NFR-light so Stage 4.b can exercise
the "skip if no NFR-touching code" conditional or produce a minimal
PASS assessment.
