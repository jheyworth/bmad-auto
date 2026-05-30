# quality-gate-fail — Phase 4 quality gates surface a BLOCK

Models a run that reached natural exit (every story `done`, Codex
ran, deferred-work computed) but whose Phase 4 quality gates produced
a BLOCKing combined verdict:

- **Stage 4.a trace gate:** CONCERNS — traceability matrix shows
  partial AC coverage on 2 stories
- **Stage 4.b NFR audit:** FAIL — perf budget violated on the
  rate-limiter latency benchmark

Per SKILL.md Stage 4 combined gate logic, `CONCERNS + FAIL → BLOCK`.
The digest renders the verdict prominently so a tired operator scanning
at end-of-run sees BLOCK on first read and knows merging is not safe
until quality issues are addressed.

`K = 3`. Next-backlog-epic = 4. Retrospective still ran (4.f only
skips on HALT exit, and this is a natural exit).

## What this scenario demonstrates

- BLOCK appears as a stand-alone verdict line at the top of the
  Quality gates block — operator sees it before reading any sub-gate
  details.
- Both sub-gate verdicts (Trace=CONCERNS, NFR=FAIL) are surfaced with
  a one-line summary of the underlying issue, not just the verdict
  token.
- Next steps swap the *"continue to next epic"* reminder for an
  explicit *"address quality-gate issues before merge"* action with
  links to the matrix + NFR assessment.
- Retrospective signals reflect the gate verdict: a
  `critical_readiness=FAIL` flag is set so Stage 4.g would prompt for
  `/bmad-correct-course` on the operator's next interactive turn.

## Mock sidecars present

- `codex-available.txt` — `true`
- `deferred-work-start.snapshot` — same placeholder as natural-exit
- `epic-K-start.sha`, `epic-K-end.sha` — placeholder SHAs
- `epic-K-trace-gate.txt` — `CONCERNS` + one-line reason
- `epic-K-nfr-gate.txt` — `FAIL` + one-line reason
- `epic-K-codex-review.md` — ~25-line placeholder (runs on natural
  exit regardless of gate verdicts; Stage 4.c skip guard is HALT only)
- `epic-K-deferred-delta.md` — same shape as natural-exit-v4
- `epic-K-spike-log.md` — empty
- `epic-K-retro-signals.txt` — `critical_readiness=FAIL` (4.f surfaced
  the gate verdicts as a critical-readiness concern)
- `sprint-status.yaml` — epic 3 (3 stories) all `done`; epic 4
  backlog; epic 5 backlog
- `expected-digest.md` — the rendered digest

## Budget target

50 lines. Actual: 40 lines. PASS.

## Expected verification points

| # | Criterion | Where in digest |
|---|---|---|
| 1 | Status reads `Completed naturally` | line 3 |
| 2 | Quality gates verdict reads `BLOCK` | line 8 |
| 3 | Trace gate shows CONCERNS + reason | line 9 |
| 4 | NFR gate shows FAIL + reason | line 10 |
| 5 | Next steps highlight gate remediation | lines 28–32 |
| 6 | Retrospective signal surfaces critical-readiness FAIL | lines 34–37 |
| 7 | Codex link still present (4.c runs on natural exit) | line 14 |
| 8 | Budget honored (≤ 50 lines) | wc -l == 40 |
