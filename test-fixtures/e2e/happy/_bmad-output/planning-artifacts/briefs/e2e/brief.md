# Project Brief — bmad-auto e2e fixture

## Problem

Verify that `/bmad-auto` orchestrates a complete epic end-to-end
without operator intervention, producing the expected sidecar artifacts
and sprint-status flips.

## Goals

- Drive an Epic 99 with two trivial stories through all four phases
- Produce verifiable artifacts at every sidecar contract point
- Complete in under 60 minutes wall-clock

## Non-goals

- No UX surface (this is a test harness, not a user-facing feature)
- No external integrations
- No persistent state outside the fixture tmpdir
