# Story 99-2: Fanout file write

**Epic:** 99
**Status:** backlog

## Story

**As** the e2e harness
**I want** story 99-2 to create `e2e-fanout.txt` with content `fanout-story-99-2`
**So that** the per-story fanout loop has a real diff to validate.

## Acceptance Criteria

1. File `./e2e-fanout.txt` exists in the repo root after this story
   completes
2. File content is exactly `fanout-story-99-2\n` (one line, trailing
   newline, no other whitespace)

## Dev Notes

- This is a fixture story for the bmad-auto e2e test suite. Keep the
  implementation as simple as possible — a single `printf` or `echo`
  is sufficient.
- No tests are required beyond the AC verification (the ATDD checklist
  will scaffold one — that's fine).
- Do NOT add anything beyond what the ACs specify. Extra files,
  comments, or refactors will fail the assertion suite.
