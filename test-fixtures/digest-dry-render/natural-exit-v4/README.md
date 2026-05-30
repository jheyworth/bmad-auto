# natural-exit-v4 — Express happy-path digest with v4 sections

Models the v4 "happy path" run: Express mode, epic 3 with 3 stories
(K-1 tracer + K-2 + K-3), all stories reached `status: done`, both
Phase 4 quality gates returned PASS, retrospective auto-spawned at
Stage 4.f and surfaced nothing critical, no spike-log deferrals or
blocks. The digest renders the full v4 canonical layout (SKILL.md
Stage 4.e), including the new sections:

- **Quality gates** (Trace + NFR — both PASS)
- **Spike triage** (zero entries — log empty)
- **Retrospective signals** (clean — no significant-discoveries, no
  critical-readiness FAIL)

`K = 3`. Next-backlog-epic lookup resolves to `4` (lowest backlog epic
with at least one non-`done` story).

## What this scenario demonstrates

- The new "Quality gates" block sits directly under the run-meta
  block (Status / Mode / Duration / Stories) and above the Codex
  review line. Both PASS lines read cleanly.
- The "Spike triage" line collapses to a single short line when the
  spike-log is empty (per SKILL.md Stage 4.e: *"see
  epic-K-spike-log.md if non-empty"*).
- The "Retrospective" sub-section under Next steps reads
  *"Retrospective: completed — no critical signals"*. This is the
  v4-introduced surfacing of `epic-K-retro-signals.txt`.

## Mock sidecars present

- `codex-available.txt` — `true`
- `deferred-work-start.snapshot` — same placeholder as v3
  natural-exit
- `epic-K-start.sha`, `epic-K-end.sha` — placeholder SHAs
- `epic-K-trace-gate.txt` — single-line gate decision (`PASS`)
- `epic-K-nfr-gate.txt` — single-line gate decision (`PASS`)
- `epic-K-codex-review.md` — ~25-line placeholder Codex review
- `epic-K-deferred-delta.md` — re-uses the v3 natural-exit counts
  (2 scope-split + 3 review-finding + 1 ambiguous)
- `epic-K-spike-log.md` — header only (zero triage entries)
- `epic-K-retro-signals.txt` — `significant_discoveries=false`,
  `critical_readiness=PASS`
- `sprint-status.yaml` — epic 3 (3 stories) all `done`; epic 4
  backlog; epic 5 backlog
- `expected-digest.md` — the rendered digest

## Budget target

50 lines (one tall-terminal screen). Actual: 34 lines. PASS.

## Expected verification points

| # | Criterion | Where in digest |
|---|---|---|
| 1 | Status reads `Completed naturally` | line 3 |
| 2 | Quality gates: Trace PASS + NFR PASS | lines 8–10 |
| 3 | Codex review link present | line 12 |
| 4 | Deferred-work counts inline | line 14 |
| 5 | Tracer docs paths fully qualified | line 17 |
| 6 | Spike triage shows empty | line 19 |
| 7 | Next steps include retrospective signal status | lines 29–30 |
| 8 | Next-backlog-epic resolves to 4 | lines 31–32 |
| 9 | Budget honored (≤ 50 lines) | wc -l == 34 |
