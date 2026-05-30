# quality-gate-waived — Trace gate WAIVED with documented risk

Models a run where the operator (or test architect) consciously waived
the traceability gate with a documented rationale. NFR audit returned
PASS. Per SKILL.md Stage 4.a, WAIVED is a first-class gate verdict
distinct from PASS / CONCERNS / FAIL — the gate did not pass on
machine-checked criteria, but the operator accepted the residual risk
in writing.

This scenario demonstrates that the digest does not hide the WAIVED
verdict behind a "PASS-equivalent" treatment; the operator scanning
the digest sees the waiver, the rationale, and the proceed signal
in the same visual block.

`K = 3`. Next-backlog-epic = 4. Retrospective ran cleanly.

## What this scenario demonstrates

- Combined-gate verdict line reads `PROCEED (with documented risk)`,
  NOT `PASS` — the waiver is surfaced verbatim, not laundered.
- Trace gate line shows `WAIVED` + the one-line waiver rationale
  ("tracer-only coverage acceptable for this internal tool — no
  external API surface, single-tenant deployment").
- NFR gate line shows `PASS`.
- Next steps include the waiver rationale as a "decision log" entry
  so the merge reviewer sees it without opening the matrix file.
- Retrospective `critical_readiness=PASS` (the waiver was a
  legitimate engineering decision, not deferred risk).

## Mock sidecars present

- `codex-available.txt` — `true`
- `deferred-work-start.snapshot` — same placeholder
- `epic-K-start.sha`, `epic-K-end.sha` — placeholder SHAs
- `epic-K-trace-gate.txt` — `WAIVED` + rationale
- `epic-K-nfr-gate.txt` — `PASS`
- `epic-K-codex-review.md` — ~22-line placeholder Codex review
- `epic-K-deferred-delta.md` — minimal (1 scope-split, 1
  review-finding, 0 ambiguous)
- `epic-K-spike-log.md` — empty
- `epic-K-retro-signals.txt` — clean
- `sprint-status.yaml` — epic 3 (3 stories) all `done`
- `expected-digest.md` — the rendered digest

## Budget target

50 lines. Actual: 37 lines. PASS.

## Expected verification points

| # | Criterion | Where in digest |
|---|---|---|
| 1 | Status reads `Completed naturally` | line 3 |
| 2 | Combined gate verdict reads `PROCEED (with documented risk)` | line 8 |
| 3 | Trace gate WAIVED + rationale visible | lines 9–10 |
| 4 | NFR PASS visible | line 11 |
| 5 | Waiver rationale repeated in next-steps decision-log entry | lines 28–30 |
| 6 | Retrospective signal clean | line 31 |
| 7 | Budget honored (≤ 50 lines) | wc -l == 37 |
