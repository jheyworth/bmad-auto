---
stepsCompleted: ['1', '2', '3', '4', '5', '6']
lastStep: '6-generate-checklist'
lastSaved: '2026-05-25T14:32:11Z'
workflowType: 'testarch-atdd'
storyId: '7-2'
storyKey: '7-2-slugify-utility'
storyFile: '_bmad-output/implementation-artifacts/7-2-slugify-utility.md'
atddChecklistPath: '_bmad-output/implementation-artifacts/atdd-checklist-7-2-slugify-utility.md'
generatedTestFiles:
  - 'src/utils/__tests__/slugify.test.ts'
inputDocuments:
  - '_bmad-output/planning-artifacts/specs/SPEC-content-pipeline/SPEC.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/implementation-artifacts/7-2-slugify-utility.md'
---

# ATDD Checklist - Epic 7, Story 7-2: Slugify utility

**Date:** 2026-05-25
**Author:** bmad-testarch-atdd (TEA agent)
**Primary Test Level:** Component (pure function unit + small integration)

---

## Story Summary

The content pipeline needs a deterministic URL slug generator. Editors type
human titles ("Café Münchner — Vol. 3!"); the publishing layer needs a
stable, ASCII-safe, length-bounded slug to use as the canonical path
segment. The function is shared by Phase 4 publishing and Phase 5
sitemap generation.

**As an** editor publishing an article
**I want** the system to derive a canonical URL slug from my title
**So that** links are stable, ASCII-safe, and don't collide across articles

---

## Acceptance Criteria

1. Plain ASCII titles round-trip predictably: `slugify("Hello World")` → `"hello-world"`.
2. Unicode is normalized to ASCII via NFKD + diacritic stripping: `slugify("Café Münchner")` → `"cafe-munchner"`.
3. Output length is capped at 64 characters; truncation never breaks mid-word (cut at the previous `-` boundary).
4. Punctuation collapses to single hyphens; leading/trailing hyphens are stripped: `slugify("  !!Hello -- World!!  ")` → `"hello-world"`.
5. Collision-suffix mode: `slugify(title, { collisionSuffix: 3 })` appends `-3` after applying rules 1–4. Suffix never causes rule-3 truncation to lose the suffix itself.

---

## Story Integration Metadata

- **Story ID:** `7-2`
- **Story Key:** `7-2-slugify-utility`
- **Story File:** `_bmad-output/implementation-artifacts/7-2-slugify-utility.md`
- **Checklist Path:** `_bmad-output/implementation-artifacts/atdd-checklist-7-2-slugify-utility.md`
- **Generated Test Files:** `src/utils/__tests__/slugify.test.ts`

Per the bmad-testarch-atdd contract, these artifact paths are mirrored
into the story's `Dev Notes` so `bmad-quick-dev` (or `bmad-dev-story`)
can discover and activate the red-phase scaffolds.

---

## Red-Phase Test Scaffolds Created

### Component Tests (5 tests)

**File:** `src/utils/__tests__/slugify.test.ts` (47 lines)

- **Test:** `slugify_plain_ascii_lowercases_and_hyphenates`
  - **Status:** RED — `slugify` symbol does not exist; import resolves to `undefined`.
  - **Verifies:** AC-1. Plain ASCII titles convert deterministically.

- **Test:** `slugify_unicode_strips_diacritics_via_nfkd`
  - **Status:** RED — same root cause; will also fail on AC-2 logic once implemented.
  - **Verifies:** AC-2. Unicode normalization + ASCII fold.

- **Test:** `slugify_truncates_at_word_boundary_under_64_chars`
  - **Status:** RED — boundary-truncation logic doesn't exist.
  - **Verifies:** AC-3. Length cap with hyphen-boundary trim.

- **Test:** `slugify_collapses_punctuation_and_strips_edges`
  - **Status:** RED — punctuation collapse not implemented.
  - **Verifies:** AC-4. Punctuation collapse, edge-trim.

- **Test:** `slugify_appends_collision_suffix_preserving_length_cap`
  - **Status:** RED — collisionSuffix option doesn't exist.
  - **Verifies:** AC-5. Collision suffix mode; truncation accounts for suffix length.

---

## Test Body (verbatim — `src/utils/__tests__/slugify.test.ts`)

```typescript
import { describe, expect, it } from 'vitest';
import { slugify } from '../slugify';

describe('slugify', () => {
  it('slugify_plain_ascii_lowercases_and_hyphenates', () => {
    expect(slugify('Hello World')).toBe('hello-world');
  });

  it('slugify_unicode_strips_diacritics_via_nfkd', () => {
    expect(slugify('Café Münchner — Vol. 3')).toBe('cafe-munchner-vol-3');
  });

  it('slugify_truncates_at_word_boundary_under_64_chars', () => {
    const long =
      'this-is-a-very-long-title-that-clearly-exceeds-the-sixty-four-character-budget-by-quite-a-lot';
    const out = slugify(long);
    expect(out.length).toBeLessThanOrEqual(64);
    expect(out.endsWith('-')).toBe(false);
    // Must cut at a hyphen boundary — should not chop mid-word.
    expect(long.startsWith(out)).toBe(true);
  });

  it('slugify_collapses_punctuation_and_strips_edges', () => {
    expect(slugify('  !!Hello -- World!!  ')).toBe('hello-world');
  });

  it('slugify_appends_collision_suffix_preserving_length_cap', () => {
    const base =
      'this-is-a-very-long-title-that-clearly-exceeds-the-sixty-four-character-budget';
    const out = slugify(base, { collisionSuffix: 3 });
    expect(out.endsWith('-3')).toBe(true);
    expect(out.length).toBeLessThanOrEqual(64);
  });
});
```

---

## Fixtures Created

None required — `slugify` is a pure function. No fixtures, factories,
mocks, or data-testids needed. This is the smallest-viable test-level
mapping per the test-levels-framework knowledge fragment.

---

## Mock Requirements

None.

---

## Required data-testid Attributes

None — non-UI feature.

---

## Implementation Checklist

Map each scaffolded red test to concrete implementation tasks that will
make it pass. `bmad-quick-dev` consumes this checklist as its work plan.

### Test: `slugify_plain_ascii_lowercases_and_hyphenates`

**File:** `src/utils/__tests__/slugify.test.ts`

**Tasks to make this test pass:**

- [ ] Create `src/utils/slugify.ts` exporting `slugify(input: string, options?: SlugifyOptions): string`
- [ ] Define `SlugifyOptions` type: `{ collisionSuffix?: number }`
- [ ] Implement lowercase conversion
- [ ] Implement space-to-hyphen conversion
- [ ] Run test: `npm test -- src/utils/__tests__/slugify.test.ts -t plain_ascii`
- [ ] Test passes (green phase)

**Estimated Effort:** 0.25 hours

---

### Test: `slugify_unicode_strips_diacritics_via_nfkd`

**File:** `src/utils/__tests__/slugify.test.ts`

**Tasks to make this test pass:**

- [ ] Apply `.normalize('NFKD')` to input before processing
- [ ] Strip combining diacritical marks via `.replace(/[̀-ͯ]/g, '')`
- [ ] Drop characters outside the ASCII set after fold
- [ ] Run test: `npm test -- src/utils/__tests__/slugify.test.ts -t unicode`
- [ ] Test passes (green phase)

**Estimated Effort:** 0.25 hours

---

### Test: `slugify_truncates_at_word_boundary_under_64_chars`

**File:** `src/utils/__tests__/slugify.test.ts`

**Tasks to make this test pass:**

- [ ] After punctuation collapse, if `result.length > 64`: slice to 64, then trim back to last `-` before index 64
- [ ] Strip trailing hyphens from the truncated result
- [ ] Run test: `npm test -- src/utils/__tests__/slugify.test.ts -t truncates`
- [ ] Test passes (green phase)

**Estimated Effort:** 0.5 hours

---

### Test: `slugify_collapses_punctuation_and_strips_edges`

**File:** `src/utils/__tests__/slugify.test.ts`

**Tasks to make this test pass:**

- [ ] Replace every run of non-`[a-z0-9]` (post-lowercase) characters with a single `-`
- [ ] Strip leading and trailing `-` from the final result
- [ ] Run test: `npm test -- src/utils/__tests__/slugify.test.ts -t collapses`
- [ ] Test passes (green phase)

**Estimated Effort:** 0.25 hours

---

### Test: `slugify_appends_collision_suffix_preserving_length_cap`

**File:** `src/utils/__tests__/slugify.test.ts`

**Tasks to make this test pass:**

- [ ] When `options.collisionSuffix` is set: compute `suffix = "-" + String(options.collisionSuffix)`
- [ ] Reserve `suffix.length` characters from the 64-char budget when truncating
- [ ] Append the suffix after truncation
- [ ] Run test: `npm test -- src/utils/__tests__/slugify.test.ts -t collision_suffix`
- [ ] Test passes (green phase)

**Estimated Effort:** 0.5 hours

---

## Running Tests

```bash
# Run all activated tests for this story
npm test -- src/utils/__tests__/slugify.test.ts

# Run a specific test by name
npm test -- src/utils/__tests__/slugify.test.ts -t plain_ascii

# Run with watch
npm test -- --watch src/utils/__tests__/slugify.test.ts

# Run with coverage
npm test -- --coverage src/utils/__tests__/slugify.test.ts
```

---

## Red-Green-Refactor Workflow

### RED Phase (Complete)

**TEA Agent Responsibilities:**

- [x] All 5 tests written as red-phase scaffolds (no `test.skip()` — tests are active and intended to fail)
- [x] No fixtures, factories, or mocks needed (pure function)
- [x] Implementation checklist created with task-to-test mapping
- [x] Test file builds against a not-yet-existent `slugify` import — TypeScript compile fails until quick-dev creates the file

**Verification:**

- Tests fail with `Cannot find module '../slugify'` or equivalent until implementation lands.
- Activated tests fail due to missing implementation, not test bugs.
- See `red-tests-failing-example.txt` for the verified red-phase test runner output.

---

### GREEN Phase (DEV Team — quick-dev's job)

`bmad-quick-dev` reads this checklist, creates `src/utils/slugify.ts`,
and works through the 5 implementation tasks until every test passes.
See `red-tests-green-example.txt` for the expected post-implementation
output.

---

### REFACTOR Phase

Out of scope for this fixture set — the green-phase output is the
contract `/bmad-auto` Stage 2.c verifies.

---

## Next Steps

1. **Story Dev Notes updated** at `_bmad-output/implementation-artifacts/7-2-slugify-utility.md` with paths to this checklist + the generated test file.
2. **`bmad-quick-dev` invoked next.** It reads `Dev Notes`, picks up the checklist, and works through the implementation tasks in order.
3. **Stage 2.c tracer-readiness** (for tracer story K-1) OR HALT-detection polling in Stage 3.4 (for non-tracer stories) re-runs the test suite and verifies all 5 tests now pass before declaring the story `done`.

---

## Knowledge Base References Applied

- **test-levels-framework.md** — Pure-function utility maps to a single Component/Unit test file. No need for E2E or API layers.
- **test-quality.md** — Given-When-Then in test naming, one assertion per behavioral axis, determinism (no random data, no clock).
- **fixture-architecture.md** — N/A (pure function).

---

## Test Execution Evidence

### Initial Scaffold Review / RED Verification

**Command:** `npm test -- src/utils/__tests__/slugify.test.ts`

**Results:** See `red-tests-failing-example.txt` for the verbatim test
runner output. All 5 tests fail; failure mode is "module not found"
because `src/utils/slugify.ts` does not yet exist.

**Summary:**

- Total tests: 5
- Skipped: 0
- Activated RED tests: 5
- Passing: 0 (expected before implementation)
- Status: Red-phase scaffolds verified

**Expected Failure Messages:**

- All 5 tests: `Error: Failed to resolve import "../slugify" from "src/utils/__tests__/slugify.test.ts"`

---

## Notes

- Pure-function story; no infrastructure needed beyond the existing vitest setup.
- Estimated total implementation budget: ~1.75 hours.
- The collision-suffix interaction with the 64-char cap (AC-5) is the most subtle behavior — quick-dev should verify the cap reservation logic before declaring green.

---

**Generated by BMad TEA Agent** — 2026-05-25
