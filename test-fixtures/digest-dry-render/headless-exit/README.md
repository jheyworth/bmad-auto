# headless-exit — Unattended overnight run, retrospective skipped

Models an unattended overnight run in Headless mode. Operator launched
the skill before going to bed and returns in the morning to read the
digest cold (no live context, no transcript memory). The digest is the
only artifact the operator scans before deciding whether the diff is
mergeable.

Per SKILL.md Stage 4.f: Headless mode skips the auto-spawned
retrospective unless `--with-retrospective` was passed. This scenario
models the default (no flag) path. The digest must therefore:

- NOT pretend a retrospective ran
- Surface the skip explicitly so a tired-and-cold operator does not
  misread the absence of signals as "everything is fine"
- Render every other v4 section so the operator does not need to dig
  into sidecar files to understand the run

`K = 3`. All gates PASS (so the BLOCK/WAIVED scenarios stay
separately covered). Codex ran. Deferred-delta computed normally.

## What this scenario demonstrates

- The Mode line reads `Headless` rather than `Express`.
- Retrospective is rendered explicitly as `Skipped — Headless mode
  (re-run with --with-retrospective for interactive retro)`. This is
  the load-bearing surface for the cold-read use case.
- The "Stage 4.g would prompt" line is suppressed (retro signals
  file does not exist when 4.f skipped).
- Next-backlog-epic still resolves, so the operator's morning
  decision tree is intact.

## Mock sidecars present

- `codex-available.txt` — `true`
- `deferred-work-start.snapshot` — same placeholder
- `epic-K-start.sha`, `epic-K-end.sha` — placeholder SHAs
- `epic-K-trace-gate.txt` — `PASS`
- `epic-K-nfr-gate.txt` — `PASS`
- `epic-K-codex-review.md` — ~22-line placeholder Codex review
- `epic-K-deferred-delta.md` — same shape as natural-exit-v4
- `epic-K-spike-log.md` — empty
- `sprint-status.yaml` — epic 3 (3 stories) all `done`
- `expected-digest.md` — the rendered digest

## Deliberately omitted

- `epic-K-retro-signals.txt` — Stage 4.f did not run in Headless
  mode, so this sidecar is not produced. The digest reads the file's
  absence as "Skipped — Headless mode" rather than crashing or
  defaulting to PASS. This is the inverse of the natural-exit-v4
  contract.

## Budget target

50 lines. Actual: 33 lines. PASS — leaner than Express digests
because the retrospective sub-block collapses to a one-liner.

## Expected verification points

| # | Criterion | Where in digest |
|---|---|---|
| 1 | Status reads `Completed naturally` | line 3 |
| 2 | Mode line reads `Headless` | line 4 |
| 3 | Quality gates: Trace PASS + NFR PASS | lines 8–10 |
| 4 | Retrospective rendered as `Skipped — Headless mode` | line 26 |
| 5 | Re-run hint `--with-retrospective` visible | line 26 |
| 6 | Stage 4.g auto-prompt suppressed (no "would prompt" line) | confirmed by absence |
| 7 | Next-backlog-epic resolves to 4 | lines 28–29 |
| 8 | Budget honored (≤ 50 lines) | wc -l == 33 |

## Cold-read sanity check

A reasonable test for this scenario: read only `expected-digest.md`
with no other context. Within 30 seconds, can a tired operator answer
all of:

- Did the run complete? (yes — `Status: Completed naturally`)
- Did anything go wrong? (no — gates PASS, no spike triage, deferred
  counts low)
- Did the retrospective run? (no — explicitly skipped in line 26)
- What's the next action? (last next-step line — prep epic 4)

If any answer requires opening a sidecar, the digest has failed its
cold-read contract.
