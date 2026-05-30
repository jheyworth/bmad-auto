# ATDD-mechanics fixture suite

Fixtures that document the **ATDD-then-quick-dev handoff contract** —
the v4 architectural commitment that makes tests-first explicit and
externally auditable inside `/bmad-auto`. Authored under D6v4 of the
`bmad-auto-validate-v4` build task list.

The four `.txt` test-runner fixtures plus the `atdd-checklist-example.md`
together trace one story (`7-2-slugify-utility`) through every state
transition that the per-story flow defines, from "no tests" through
either "green tests, story done" or "red tests still failing → HALT
fires".

---

## Why this fixture set exists

Two downstream consumers:

1. **G3v4 operator-run gate** (Phase 2 tracer + Phase 3 fanout) needs a
   reference for what a clean ATDD → quick-dev handoff is supposed to
   look like, so the operator can compare what they observe in a real
   run against the contract.
2. **D12v4 ATDD-quick-dev handoff tuning** reads G3v4's findings + this
   fixture set together. If the real run diverges from the artifact
   shapes documented here, D12v4 is where SKILL.md Stage 2.a / 2.b /
   3.b get patched to close the drift.

The auto-skills-design.md v4 architecture explicitly calls out tests-
first as Principle 3 and notes the ATDD wiring is the v4 contribution
most likely to surface integration issues at G3. This fixture set is
the substrate for both observing and fixing those issues.

---

## The handoff contract per SKILL.md

Source: `skills/bmad-auto/SKILL.md` (v4). Stage numbers cited verbatim.

### Stage 2.a — ATDD red-phase scaffolds (Express, tracer story K-1)

> 1. Invoke `bmad-testarch-atdd` against story K-1.
> 2. Pass story file path as input; ATDD auto-detects stack from
>    project manifests.
> 3. Wait for completion. Verify outputs:
>    - `atdd-checklist-K-1.md` (red-phase scaffold + implementation
>      checklist)
>    - Generated red test files (E2E/API/Component skeletons)
>    - Fixture stubs and helper signatures
> 4. **Validate red tests are red.** Run the test runner. Tests must
>    fail. If any pass before implementation, HALT — ATDD scaffolding
>    has a defect (likely a test that doesn't actually exercise the
>    AC).
> 5. Note path of ATDD checklist to orchestrator-session memory.

**Fixture mapping:**
- `atdd-checklist-example.md` — the shape of the artifact produced by
  step 3 (frontmatter + red-phase scaffold table + body of the
  generated test file + implementation checklist).
- `red-tests-failing-example.txt` — the verified-red output produced
  by step 4.

### Stage 2.b — Tracer implementation via quick-dev (Express)

Captured 2026-05-25 against SKILL.md v4 at G3v4 validation time. The
Format B clauses have since been stripped from SKILL.md (see
`../../../build-tasks/bmad-auto-format-b-cleanup.md` T3). The quote
below preserves the v4-at-validation snapshot for audit-trail; do not
re-sync it against current SKILL.md.

> 1. Invoke `bmad-quick-dev` against story K-1.
> 2. Quick-dev reads the K-1 story file + ATDD checklist (if present).
> 3. **Operator interacts heavily.** ... make red tests green, produce
>    micro-PRD and micro-architecture (Format A) OR
>    `solution-design.md` (Format B), surface and resolve
>    architectural decisions for the rest of epic K.

**Fixture mapping:**
- The checklist's `Implementation Checklist` section (one task block
  per red test) is the work plan quick-dev consumes.
- On success: `red-tests-green-example.txt` is the resulting test run.
- On exhaustion: `red-tests-still-failing-example.txt` is the resulting
  test run — and the trigger for the v4 HALT.

### Stage 2.c — Tracer-readiness gate

Captured 2026-05-25 against SKILL.md v4 at G3v4 validation time. The
Format B clauses have since been stripped from SKILL.md (see
`../../../build-tasks/bmad-auto-format-b-cleanup.md` T3). The quote
below preserves the v4-at-validation snapshot for audit-trail; do not
re-sync it against current SKILL.md.

> Checks:
> 1. Sprint-status: K-1 story key has value `done`
> 2. Format A: ... both micro-PRD and micro-architecture exist with all
>    required sections non-empty
> 3. Format B: solution-design.md exists with all required sections
>    non-empty
> 4. **Red tests from Stage 2a now pass (if `--skip-atdd` was not
>    used). Run the test runner against K-1's tests.**

**Fixture mapping:**
- Check #4 PASS ↔ `red-tests-green-example.txt`.
- Check #4 FAIL ↔ `red-tests-still-failing-example.txt`. Tracer-
  readiness fails; Stage 2.c HALTs with the failure-mode message per
  `references/tracer-readiness-check.md`.

The tracer-readiness check is the **architectural enforcement** of
tests-first for the tracer story. The story may not advance to Phase 3
fanout unless every red test from Stage 2.a went green.

### Stage 3.b — Per-story ATDD (autonomous, in tmux)

For each non-tracer story K-2..K-N, the `/goal` directive composed in
Stage 3.1 embeds the chained per-story workflow verbatim:

> Execute via bmad-testarch-atdd (red-phase scaffolds) THEN
> bmad-quick-dev (implementation makes red green) THEN
> bmad-testarch-automate (or bmad-qa-generate-e2e-tests for coverage
> expansion, non-blocking) THEN bmad-code-review.
>
> ...
>
> Mark sprint-status.yaml story key to `done` only when:
> - ATDD red tests authored
> - bmad-quick-dev makes them green AND produces clean implementation
> - code-review passes

**Fixture mapping:**
- Same four `.txt` fixtures apply per non-tracer story; the only
  difference vs Phase 2 is topology (tmux subprocess vs in-session).
- The orchestrator does not directly run the test runner for non-
  tracer stories. Enforcement is via:
  1. The story spawned in tmux reads the `/goal` directive's `done`-
     criteria contract.
  2. If the spawned session marks the story `done` while red tests
     still failing, Stage 3.4 capture-pane HALT detection catches the
     trigger substrings `red tests still failing` / `tests not green`
     and aborts the run.

---

## Expected test states at each transition

Cited from `skills/bmad-auto/SKILL.md` Stage 2.a–2.c and Stage 3.b /
3.4. Read in order:

| Transition | Fixture | Test state |
| --- | --- | --- |
| Pre-ATDD (story created, no tests yet) | _(no fixture; absence-of)_ | No test file exists. `npm test -- src/utils/__tests__/slugify.test.ts` would error with "no test files found". |
| Post-ATDD, pre-implementation (Stage 2.a step 4 / Stage 3.b ATDD complete) | `red-tests-failing-example.txt` | 5/5 tests fail, all on `Failed to resolve import` — proves tests exist + are wired to a not-yet-present implementation. Stage 2.a step 4 PASSES (tests are red as expected). |
| Post-implementation success (Stage 2.b complete, Stage 2.c gate PASS) | `red-tests-green-example.txt` | 5/5 tests pass. Stage 2.c check #4 PASSES → story advances to Phase 3. For non-tracer stories: spawned tmux session is allowed to mark sprint-status `done`. |
| Post-implementation failure (Stage 2.b exhausted, Stage 2.c gate FAIL) | `red-tests-still-failing-example.txt` | 3/5 pass, 2/5 still red after the iteration budget. For Phase 2 (tracer): Stage 2.c HALTs with tracer-readiness failure. For Phase 3 (non-tracer): Stage 3.4 capture-pane detects the trigger substrings and HALTs the run. **In both cases the story is NOT marked done.** |

The four states form a directed graph with two terminal states:

```
no tests
   │
   ▼
ATDD ─────────────────► red tests authored
   │                        │
   │                        ▼
   │                  quick-dev iterates
   │                        │
   │             ┌──────────┴──────────┐
   │             ▼                      ▼
   │      all tests green        red tests still failing
   │             │                      │
   │             ▼                      ▼
   │      Stage 2.c PASS         Stage 2.c FAIL
   │      story → done              HALT fires
```

The `red-tests-still-failing-example.txt` fixture documents the right-
hand terminal state. The architectural commitment: this state must
HALT, never silently mark the story done.

---

## Connection to the D1v4 HALT trigger

D1v4 added two trigger substrings to SKILL.md Stage 3.4's HALT-detection
table:

| Trigger substring | Class |
| --- | --- |
| `red tests still failing` or `tests not green` | Tests-first commitment violation — ATDD red tests never went green |

D1v4 captured this from the operator-facing tmux trace at
`skills/bmad-auto/test-fixtures/halt-detection/trigger-red-tests-failing.txt`
— the **operator's-view** artifact of what Stage 3.4 sees when polling
`tmux capture-pane`.

D6v4 (this fixture set) captures the **test-runner-view** artifact of
the same condition:

- `red-tests-still-failing-example.txt` shows the literal test runner
  output that the spawned tmux process sees and prints just before
  emitting the HALT status line.
- The closing summary block in that fixture (`# bmad-quick-dev exit
  summary ...` through `Status: HALTED. red tests still failing —
  tests not green at quick-dev exit.`) is consistent with what the
  D1v4 trigger fixture captures one level up from the tmux pane.

In production:
1. quick-dev's RGR loop exhausts → quick-dev prints its exit summary
   including the literal substrings `red tests still failing` and
   `tests not green` (D6v4 fixture).
2. The orchestrator's Stage 3.4 polling reads the pane, matches one or
   both substrings against the trigger table (D1v4 fixture).
3. The orchestrator captures the pane to
   `epic-K-story-<id>-halt-context.txt`, kills the tmux session, and
   takes the HALT-exit branch (Stage 3.C.2).

The two fixture sets are **paired by design** — together they
demonstrate that the test-runner output, quick-dev's exit prose, and
the orchestrator's HALT-detection token all share a deterministic
substring vocabulary.

---

## Story chosen for the fixture set

**Story `7-2-slugify-utility`** — a deterministic URL slug generator
for a hypothetical content pipeline. Five ACs:

1. Plain ASCII titles round-trip predictably
2. Unicode is normalized via NFKD + diacritic stripping
3. Length cap at 64 chars with hyphen-boundary truncation
4. Punctuation collapse + edge trim
5. Collision-suffix mode preserving the length cap

Why this choice:

- **Realistic but small.** Pure function, single test file, no
  fixtures or mocks needed. The ATDD checklist is small enough to read
  in one screen; the test output fits comfortably in tmux capture-
  pane's default `-S -200` lookback budget.
- **Clear pass/fail per AC.** Each test maps to exactly one AC; the
  `still-failing` fixture can plausibly stall on AC-3 (boundary-
  truncation) and AC-5 (collision suffix budget) — both subtle enough
  that a 5-iteration RGR exhaustion is realistic, not contrived.
- **Framework match.** TypeScript + vitest is the most common stack
  the v4 ATDD wiring will encounter in practice. The output format
  (RUN/FAIL/PASS banners, file paths, AssertionError diffs) is
  recognizable to any operator reading the digest's tail-trimmed
  HALT context.

Framework: **vitest 1.6.0 / TypeScript / npm test**.

---

## Cross-references

- `SKILL.md (Stage 4.a/4.b)` § "bmad-testarch-atdd LOAD-
  BEARING" — the contract spec for the skill's inputs and outputs
  that this fixture set illustrates.
- `SKILL.md (Stage 4.a/4.b)` § "Recommendation for
  /bmad-auto Phase 3 redesign" — the 5-step per-story flow this
  fixture set sits inside.
- `docs/auto-skills-design.md` § "Principle 3 — Tests-first is
  architecturally enforced" — the architectural commitment this
  fixture set validates.
- `skills/bmad-auto/SKILL.md` Stage 2.a, 2.b, 2.c, 3.1 (`/goal`
  composition), 3.4 (HALT detection) — the runtime instructions that
  consume these artifact shapes.
- `skills/bmad-auto/references/tracer-readiness-check.md` § "Failure
  modes" — the Stage 2.c failure-mode message catalog that pairs with
  `red-tests-still-failing-example.txt`.
- `skills/bmad-auto/test-fixtures/halt-detection/trigger-red-tests-
  failing.txt` (D1v4) — paired operator-view tmux trace for the
  same scenario this fixture set models from the test-runner side.
- `skills/bmad-auto/test-fixtures/halt-detection/README.md` (D1v4) —
  the trigger substring table this fixture set's output prose
  deliberately hits.
- `.claude/skills/bmad-testarch-atdd/atdd-checklist-template.md` —
  the canonical frontmatter shape that `atdd-checklist-example.md`
  follows.

---

## File index

| File | Role |
| --- | --- |
| `atdd-checklist-example.md` | Example output from `bmad-testarch-atdd` for story `7-2-slugify-utility`. Frontmatter + ACs + scaffold list + verbatim test body + implementation checklist. |
| `red-tests-failing-example.txt` | Pre-implementation vitest run. 5/5 fail on missing module. Stage 2.a step 4 passes with this output. |
| `red-tests-green-example.txt` | Post-implementation vitest run. 5/5 pass. Stage 2.c check #4 passes with this output. |
| `red-tests-still-failing-example.txt` | Post-quick-dev-exhaustion vitest run. 3/5 pass, 2/5 still red on AC-3 + AC-5 edge cases. Closing block emits the HALT substrings that pair with the D1v4 trigger fixture. |
| `README.md` | This document. |
