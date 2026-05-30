# Epics — bmad-auto e2e fixture

## Epic 99: e2e orchestrator verification

**Goal:** Verify `/bmad-auto` orchestrates two trivial stories end-to-end.

**Stories:**

### 99-1: Tracer file write

**As** the e2e harness
**I want** story 99-1 to create `e2e-tracer.txt` with `tracer-story-99-1`
**So that** the tracer-readiness gate has a real diff to validate.

**Acceptance criteria:**

1. File `./e2e-tracer.txt` exists after story completion
2. File content is exactly `tracer-story-99-1\n`

### 99-2: Fanout file write

**As** the e2e harness
**I want** story 99-2 to create `e2e-fanout.txt` with `fanout-story-99-2`
**So that** the per-story fanout loop has a real diff to validate.

**Acceptance criteria:**

1. File `./e2e-fanout.txt` exists after story completion
2. File content is exactly `fanout-story-99-2\n`
