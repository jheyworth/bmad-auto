# HALT-detection fixture suite

**These fixtures are inputs to the helper binary's pytest suite at
`skills/bmad-auto/scripts/tests/`.** They were originally authored as
desk-check material for SKILL.md Stage 3.4 prose (so humans could
hand-walk the heuristic against representative inputs); after the v5
helper extraction, the Stage 3.4 polling / HALT-detection / stall-
fingerprinting logic was lifted out of SKILL.md prose into the
stdlib-only helper at `skills/bmad-auto/scripts/bmad-auto-helper.py`,
and these fixtures retain their role as the canonical test inputs for
that helper's pytest suite (`test_halt_check_grep.py`,
`test_halt_check_sidecar.py`, and the `test_monitor_*.py` outcome
tests).

The canonical v4 address used throughout this README — **Stage 3.4 —
Capture-pane HALT detection + completion polling** inside the per-
story loop of Phase 3 (Autonomous fanout) — refers to the original
SKILL.md location. Earlier v3 history pointed at "stage 5.2.8.2" /
"stage 5.2.9"; the v4 renumbering folded those into Stage 3.4; v5
moved the executable heuristic into helper code. The trigger set,
guards, and outcome classes below remain the design specification the
helper implements.

## Source-of-truth (originally verbatim from SKILL.md Stage 3.4 v4; now implemented in `bmad-auto-helper.py`)

> **HALT detection — case-insensitive substring matching against the
> captured output, with structural guards.** Triggers (per D6 tuning +
> tests-first additions):
>
> | Trigger substring | Class |
> | --- | --- |
> | `intent_gap` | Quick-dev intent gap surfaced |
> | `bad_spec` | Quick-dev bad-spec finding |
> | `VCS dirty` | Working tree has uncommitted changes |
> | `wrong branch` | Operator's `--dev` branch is unsafe (main/master) |
> | `>5 loopbacks` or `more than 5 loopbacks` or `loopback ceiling` | Quick-dev iteration limit hit |
> | `HALT` (literal, on a line by itself OR as a clear status — NOT as a noun in English prose) | Explicit HALT from quick-dev or operator |
> | `red tests still failing` or `tests not green` | Tests-first commitment violation — ATDD red tests never went green |

> **Conservative wins:** when in doubt about a match, treat it as a
> HALT and surface. False-positive HALTs are recoverable (the operator
> inspects and re-runs); missed HALTs corrupt the run silently.

the helper halt-detection notes § "Known limitations" confirms this is heuristic by design
and that the project accepts conservative HALT-on-doubt as the chosen
posture. Tuning the parser happened in D11v4 based on the operator's
G3v4 findings; D1v4 (this directory) staged the initial fixtures.

### D11v4 tuning — structural guards (Deviation #7 fix)

Substring matching alone false-positives when HALT-class tokens appear
in /goal prompt prose (the /goal directive embeds the autonomous-mode
directives verbatim, which themselves mention `HALT`, `intent_gap`,
`VCS dirty`, `wrong branch`, etc as instructional content). G3v4
captured this — the operator hand-tuned the live poll loop on top of
the v3 baseline. D11v4 codified three structural guards (originally in
SKILL.md Stage 3.4 prose, now implemented in `check_halt` /
`_apply_tail_window` inside `bmad-auto-helper.py`). A candidate match
(any line containing a trigger substring case-insensitive) must pass
ALL three guards to count as a real HALT:

1. **Tail-window guard.** Match must appear in the **last 60 lines**
   of the capture-pane buffer. /goal prompt prose lives at the top of
   the buffer; once the spawned claude has produced meaningful work,
   the prompt slides out of the tail window. Matches outside the tail
   window are prompt scrollback, not event output — suppress.
2. **Prose-line suppression.** Suppress the candidate if the line
   matches instructional/prose patterns: leading `> ` (markdown quote
   prefix — common when claude echoes back the /goal directive),
   leading conditional/modal (`if`, `when`, `should`, `must`,
   `unless`) after optional bullet, or the trigger token wrapped in
   backticks / quotation marks. Conservative bias: if the line is a
   clear status emission (`Status: HALTED.` / `Reason: intent_gap` /
   etc), prose-suppression does NOT fire.
3. **HALT-literal discrimination** (pre-existing). The bare `HALT`
   substring still requires the "on a line by itself OR as a clear
   status — NOT as a noun in English prose" qualifier.

### D11v4 tuning — primary-vs-secondary terminal signal

Sprint-status flip to `done` is the **primary** terminal signal.
Printed string markers in the capture-pane (e.g. `STORY_K-N_DONE`)
are *advisory secondary signal* only. Rationale: the /goal prompt
itself contains the literal marker string (it must, in order to
instruct the print); prompt scrollback is indistinguishable from real
output under substring grep. The G3v4 operator hand-walked through
three mitigations of this and converged on "sprint-status is the
authoritative signal; capture-pane grep is diagnostic-only".

### D11v4 tuning — new STALL outcome (Deviation #8 fix)

A new third outcome joins `done` and `HALT`: `stalled`. A spawned
session that finishes work but never emits the sprint-status flip
(or HALT trigger) appears silent to the orchestrator — neither
completion nor failure. Stall detection layers on top of the HALT/
done detection: the orchestrator hashes the capture-pane buffer
each poll and maintains a rolling 3-poll fingerprint history. STALL
fires when ALL of: 3 consecutive identical fingerprints, sprint-
status NOT done, no HALT trigger fired, AND the story has been
running for at least 5 minutes (so first-prompt-parse think-time
doesn't trip the detector).

STALL surfaces to the operator with the recommended action of
attaching to the tmux session and either nudging it or killing-and-
rerunning. STALL ≠ HALT: it's "session alive but not progressing".
Loop-exit branching adds a new 3.C.3 STALL branch (does not advance
to Phase 4, holds the run for operator triage).

Stall detection currently assumes the 45s polling cadence (3 polls
≈ 2.25 minutes wall-clock to trip). D15v4 may retune cadence; the
3-poll count remains correct but wall-clock scales.

### What changed v3 → v4 in the trigger set

v3 published 5 trigger classes (`intent_gap`, `VCS dirty`, `wrong
branch`, the loopback aliases, the bare `HALT` literal). v4 added two
trigger classes per the tests-first commitment + bad-spec robustness:

- **`bad_spec`** — quick-dev surfaces a bad-spec finding (spec is
  internally inconsistent or unimplementable). No positive fixture
  authored in this directory yet; flagged as a coverage gap below.
- **`red tests still failing` / `tests not green`** — the tests-first
  commitment violation trigger. Fixture set added in D1v4 (see new
  rows in the inventory table). Rationale: per auto-skills-design.md
  Principle 3 + non-negotiable #8, ATDD red tests are externally
  auditable artifacts and `bmad-quick-dev` is expected to drive them
  green. If quick-dev exits with red tests still red, the story is
  *not* done and the run must HALT rather than silently mark done.

## Substring set under test

```
intent_gap
bad_spec
VCS dirty                 (case-insensitive, so "vcs dirty" matches too)
wrong branch
>5 loopbacks
more than 5 loopbacks
loopback ceiling
HALT                      (with the "line-by-itself or clear status" qualifier)
red tests still failing
tests not green
```

All but `HALT` are plain case-insensitive substring matches. Only
`HALT` has structural context written into the rule, and that's the
discrimination most likely to be where the heuristic is on a knife's
edge. The new `red tests still failing` / `tests not green` pair is
likely to share a discrimination concern with the historical
`intent_gap`-resolved case: a story discussing the trigger phrases as
methodology prose will substring-match without being an actual HALT.

## Fixture inventory and expected classification

| Fixture | Expected | Driving substring(s) | Notes |
| --- | --- | --- | --- |
| `trigger-intent-gap.txt` | **HALT** | `intent_gap` (x2), `HALT` as status (x2) | Quick-dev surfaces an intent gap between AC-3 and the tracer architecture's tiered-window pattern. Both `intent_gap` and a final `Status: HALTED.` line are present. |
| `trigger-bad-spec.txt` | **HALT** | `bad_spec` (x6), `HALT` as status (x4) | **README-follow-up NEW (2026-05-26).** Quick-dev's Step-2 intent reconciliation finds story 5-2-export-csv's spec internally inconsistent: AC-1 (streaming export with 50MB memory ceiling) contradicts AC-4 (global sort across full result set), and `paginated_query()` helper referenced in Implementation notes does not exist in `src/db/`. Closes the D1v4 bad_spec coverage gap flagged in the README follow-ups section + fixture-count summary. Sidecar paired with `sidecar-bad-spec.json` (the structured-signal twin of this capture-pane fixture; same scenario, same story id). |
| `trigger-vcs-dirty.txt` | **HALT** | `VCS dirty` (x2), `HALT` as status (x3) | Quick-dev's Step-1 VCS sanity check finds three unstaged paths and surfaces "VCS dirty". |
| `trigger-wrong-branch.txt` | **HALT** | `wrong branch` (x2), `HALT` as status (x2) | Current branch is `main`; the auto-dev refusal list rejects it. The phrase "wrong branch detected" appears verbatim. |
| `trigger-loopback-overflow.txt` | **HALT** | `>5 loopbacks` (x1), `more than 5 loopbacks` (x1), `loopback ceiling` (x2), `HALT` as status (x1) | Iteration 6 of one story exceeds the loopback budget. Multiple aliases co-occur, matching the SKILL.md "also match" expansion. |
| `trigger-explicit-halt.txt` | **HALT** | `HALT` on a line by itself (x1) + `HALTED` as status (x2) | No other trigger substring appears. The fixture exercises the bare-`HALT`-on-a-line case from SKILL.md's discrimination rule. |
| `trigger-red-tests-failing.txt` | **HALT** | `red tests still failing` (x2), `tests not green` (x2), `HALT` as status (x1) | **v4 NEW.** Quick-dev exhausts its iteration budget on story 4-3 with 2 of 4 ATDD-authored tests still red (AC-3 flake + AC-Ops clock-skew). Per the tests-first commitment the story is not done. Multiple aliases of the new trigger co-occur, matching the SKILL.md Stage 3.4 "also match" expansion (`tests not green`). |
| `negative-clean-progress.txt` | **NOT-HALT** | (none) | Vanilla story execution finishing `done`. A correct parser must classify this NOT-HALT; a buggy one that flags any uncommon string would still pass here. The control case. |
| `negative-loopback-count-2.txt` | **NOT-HALT** | (none of the trigger substrings) | Quick-dev runs iteration 2 of N (well under the 5-iteration ceiling). Contains `loopback counter`, `loopback risk`, `loopback budget` — none of which match the documented trigger substrings. Confirms that the parser is not over-broad on the word "loopback". |
| `negative-branch-discussion.txt` | **NOT-HALT** (ambiguous — see flags below) | `HALT` (x1) | The phrase "git branching strategy" never uses "wrong branch". The single `HALT` occurrence is "this is an aside captured for operator review, not a HALT condition" — English prose, not a status. Per SKILL.md's `HALT`-discrimination rule this should NOT count, but a naive substring matcher will false-positive. |
| `negative-intent-gap-resolved.txt` | **NOT-HALT** (ambiguous — see flags below) | `intent_gap` (x2), `halt`/`halted` (x3) | Quick-dev resumes story 5-3 after the operator amended the spec, and explicitly narrates that the prior `intent_gap` is now resolved and the story completes `done`. A naive substring matcher WILL false-positive; a correct heuristic needs to read the surrounding "is now resolved" / "Status: done" context. This is the most realistic false-positive risk on actual operator runs. |
| `negative-mention-of-halt-in-spec.txt` | **NOT-HALT** (ambiguous — see flags below; heaviest false-positive risk) | `intent_gap` (x1), `VCS dirty` (x1), `wrong branch` (x2), `>5 loopbacks` (x1), `loopback ceiling` (x1), `HALT` (x8) | Quick-dev is documenting the monitor-loop's HALT-detection behavior as a documentation-only story. Every trigger substring appears as a quoted spec fragment or descriptive prose. A naive substring matcher false-positives on all of them; a correct heuristic would need to recognize that the story spec itself is about HALT semantics. Pre-stages a near-worst-case scenario for G3 to surface. |
| `negative-red-tests-discussion.txt` | **NOT-HALT** (ambiguous — see flags below) | `red tests still failing` (x2), `tests not green` (x2), `HALT` (x1 as noun) | **v4 NEW.** Quick-dev is writing methodology prose about the red-green-refactor cycle and the tests-first commitment. The new trigger substrings appear ONLY as quoted descriptions of how the HALT trigger works; the actual doctests transition red→green and the story exits `done` cleanly. A naive substring matcher WILL false-positive on the new trigger; a correct heuristic needs the same resolved-vs-current discrimination flagged for `negative-intent-gap-resolved.txt`. |
| `negative-halt-in-prompt-scrollback.txt` | **NOT-HALT** (resolves cleanly under D11v4 guards) | `intent_gap` (x1, in prompt), `VCS dirty` (x1, in prompt), `wrong branch` (x1, in prompt), `>5 loopbacks` (x1, in prompt), `bad_spec` (x1, in prompt, conditional-`If`-prefixed), `HALT` (x4, in prompt — all in markdown-quote-prefixed prompt prose), zero matches in healthy completion below | **D11v4 NEW.** The /goal directive at the top of the buffer (lines 1–24, rendered with markdown-quote prefix as claude echoes back the prompt) contains nearly every trigger substring as instructional content. The healthy completion (sprint-status flip to `done`, `STORY_7-2_DONE` marker) sits in the bottom half of the buffer. The fixture is 85 lines; tail-window guard (last 60 lines = lines 26–85) suppresses the lines 11/14/15/23 prompt matches. The one prompt-prose match that does fall in the tail window (line 33 — "If the spec is internally inconsistent, surface bad_spec and HALT.") is suppressed by guard #2 (leading markdown-quote prefix AND leading conditional `If`). Classification: **NOT-HALT** under tuned logic. Pre-D11v4 naive substring matcher would false-positive on all of them. |
| `trigger-stall-no-terminal-marker.txt` | **STALL** (new v4 outcome) | (zero HALT-trigger substrings in tail window) | **D11v4 NEW.** Spawned claude finished implementation + code-review + tests-green cleanly, then idled at the prompt without updating sprint-status.yaml and without printing the completion marker. Capture-pane shows no further output after the "Implementation complete. Code review clean. Tests green." line. In a live run, the capture-pane fingerprint would be stable across 3 consecutive polls; sprint-status remains `ready-for-dev`; no HALT trigger fires. Per the new stall layer, this fixture exercises the third outcome class (`stalled`) added in D11v4. Classification: **STALL**. This is the Deviation-#8 mode the G3v4 operator hit on story 99-2; the new outcome surfaces it explicitly rather than letting polling silently hit the 1-hour session timeout. |

## Per-fixture classification (originally authored as a SKILL.md Stage 3.4 desk-check)

This section was originally a desk-check walkthrough of the v3 prose
at SKILL.md 5.2.8.2 / Stage 3.4 against each fixture; post-v5 it
remains useful as the per-fixture expected-classification narrative,
which the pytest suite at `skills/bmad-auto/scripts/tests/` asserts
against in code. The walk-through mirrors what the helper does during
a real `bmad-auto --dev` run: read the fixture top-to-bottom as if it
were a `tmux capture-pane -p` output, perform case-insensitive
substring matching against the published set, then for any `HALT`
occurrence apply the "line-by-itself or clear status" discrimination
rule (plus the D11v4 structural guards).

### Positive (trigger) fixtures — all unambiguously HALT

- **`trigger-intent-gap.txt`** — `intent_gap` (substring, twice) AND
  `Status: HALTED.` on a line of its own. Either match alone is
  sufficient; both together leave zero ambiguity. **Classification:
  HALT.** Reason string per SKILL.md: `intent_gap`.

- **`trigger-bad-spec.txt`** (README-follow-up NEW, 2026-05-26) —
  `bad_spec` appears six times in the spec-reconciliation narration
  and final status block; `Status: HALTED. bad_spec — ...` on a line
  of its own. All matches sit in the tail-window (file is 77 lines,
  tail starts at line 18); none are wrapped in backticks/quotes; no
  leading conditional/modal or markdown-quote prefix. **Classification:
  HALT.** Reason string per SKILL.md: `bad_spec`. Closes the D1v4
  coverage gap that was flagged here for ten review cycles (G5v4 →
  G6v4 → G7v4 → cleanup → cadence work → this one). Story
  5-2-export-csv's AC-1 vs AC-4 contradiction is the same scenario
  used by `sidecar-bad-spec.json` so the capture-pane and sidecar
  exemplars share a single internally-consistent narrative.

- **`trigger-vcs-dirty.txt`** — `VCS dirty:` appears in body text and
  in the reason line; `Status: HALTED.` line of its own.
  **Classification: HALT.** Reason string: `VCS dirty`.

- **`trigger-wrong-branch.txt`** — `wrong branch detected:` in the
  body; `Reason: wrong branch (...)` parenthesized; `Status: HALTED.`
  line of its own. **Classification: HALT.** Reason string:
  `wrong branch`.

- **`trigger-loopback-overflow.txt`** — All three loopback aliases co-
  occur: `>5 loopbacks`, `more than 5 loopbacks`, and `loopback
  ceiling`. `Status: HALTED on loopback ceiling.` is a single-line
  status. **Classification: HALT.** Reason string: `>5 loopbacks`.

- **`trigger-explicit-halt.txt`** — The token `HALT` appears alone on
  a line (immediately before the "Story: 3-6-export-pipeline" block,
  styled as a status delimiter). The other matches (`HALTED` in
  `Status: HALTED.`) are clear status forms, not English prose nouns.
  No other trigger substring is present. **Classification: HALT.**
  Reason string: `unspecified HALT` (the SKILL.md fallback when only
  the bare HALT literal matches).

- **`trigger-red-tests-failing.txt`** (v4 NEW) — Quick-dev runs 5
  iterations of RGR against story 4-3 (quota window reset). ATDD
  authored 4 red tests up-front; quick-dev drives 2 of them green
  but AC-3 (boundary race) and AC-Ops (clock-skew) remain red at
  exit. The phrases `red tests still failing` and `tests not green`
  appear in the reason line and in the final status line. Either
  match alone is sufficient under the SKILL.md Stage 3.4 rule;
  both together leave zero ambiguity. **Classification: HALT.**
  Reason string per SKILL.md: `red tests still failing` (the
  primary alias). The tests-first commitment violation is the
  v4-introduced HALT class this fixture exercises.

- **`trigger-stall-no-terminal-marker.txt`** (D11v4 NEW) — Spawned
  claude completes all five per-story flow steps cleanly (red ATDD
  authored, quick-dev drives green, code-review passes, tests
  green) but does not update sprint-status and does not print the
  completion marker. The capture-pane ends with "Implementation
  complete. Code review clean. Tests green." and a comment
  indicating the cursor sits idle at the prompt. No HALT trigger
  fires (correctly — there is no failure). No sprint-status flip
  fires (correctly — the spawned claude never wrote it). The new
  **stall layer** detects the 3-consecutive-identical-fingerprint
  condition and fires the STALL outcome instead. **Classification:
  STALL** under the new outcome class. This is the Deviation #8
  failure mode the G3v4 operator hit on story 99-2; the new
  outcome class surfaces it explicitly. (For desk-check purposes
  against this fixture alone, treat the entire file as a single
  poll's capture-pane buffer and observe: zero HALT-trigger
  substrings AND no `Status: done` / sprint-status-yaml-update
  marker in the buffer. In a live run, two more consecutive polls
  with byte-identical capture-pane = STALL fires.)

### Negative fixtures — expected NOT-HALT, but ambiguity flagged

- **`negative-clean-progress.txt`** — zero trigger substrings. A
  correctly-implemented parser cannot false-positive here.
  **Classification: NOT-HALT.** No ambiguity.

- **`negative-loopback-count-2.txt`** — zero trigger substrings. The
  phrases used (`loopback counter`, `loopback risk`, `loopback
  budget`) deliberately avoid the published aliases. A naive matcher
  that broadens "loopback" alone would false-positive; a matcher
  faithful to the published substring set will not.
  **Classification: NOT-HALT.** No ambiguity *if* the parser is
  faithful to the substring set as written.

- **`negative-branch-discussion.txt`** — one `HALT` occurrence, in the
  English-prose form "this is an aside captured for operator review,
  not a HALT condition". SKILL.md's discrimination rule says this
  should NOT match. The `HALT`-as-noun-in-prose is *exactly* the
  example given in the rule itself, just phrased differently.
  **Classification: NOT-HALT** under the documented rule, but a naive
  case-insensitive substring matcher that ignores the discrimination
  qualifier WILL false-positive. **Ambiguity flag: yes** — knife-edge
  case for the HALT-literal discrimination.

- **`negative-intent-gap-resolved.txt`** — `intent_gap` (substring,
  x2) and `halt`/`halted` (x3) appear, but every occurrence is
  surrounded by language describing a *resolved* prior halt and a
  *successful* current resumption ending in `Status: done`. SKILL.md's
  substring rule is positional (does the substring appear?) not
  semantic (is the substring describing a current event?), and the
  "conservative wins" posture explicitly says to treat ambiguous
  matches as HALT. **Classification under the rule as written: HALT
  (false-positive).** **Classification a human operator would
  reach: NOT-HALT.** **Ambiguity flag: yes — high-impact false-
  positive risk.** This is the most realistic real-world false-
  positive the heuristic will produce: on a `--prep` → spec-amend →
  `--dev` resumption flow, the resumed story's preamble will recap
  the prior halt and the matcher will trip on the recap.

- **`negative-mention-of-halt-in-spec.txt`** — every trigger substring
  is present multiple times because the story spec itself documents
  the substring set. SKILL.md's substring rule as written will
  classify this as HALT (with `intent_gap` as the first-matched
  reason, by top-to-bottom ordering). A human operator reading the
  fixture immediately recognizes it is a docs-only story executing
  normally. **Classification under the rule as written: HALT (false-
  positive).** **Classification a human operator would reach: NOT-
  HALT.** **Ambiguity flag: yes — catastrophic false-positive risk.**
  This is the worst-case scenario: a documentation story about the
  HALT detection logic will *always* be flagged as a HALT under the
  current heuristic. The only safe place for this story is a
  per-story session that is then operator-overridden after inspection.

- **`negative-red-tests-discussion.txt`** (v4 NEW) — `red tests still
  failing` (x2) and `tests not green` (x2) appear as quoted phrases
  inside methodology prose; one `HALT` appears as an English-prose
  noun ("the orchestrator HALTs"). The actual doctest run transitions
  red→green within 2 iterations and the story exits `Status: done`.
  Under SKILL.md Stage 3.4 as written (substring rule + conservative-
  wins) the parser will false-positive on the new trigger; a human
  operator reading the fixture immediately recognizes it is a docs-
  only story executing normally. **Classification under the rule as
  written: HALT (false-positive).** **Classification a human operator
  would reach: NOT-HALT.** **Ambiguity flag: yes — same shape as
  `negative-intent-gap-resolved.txt` but applied to the new v4
  trigger.** Under D11v4 tuned logic, most of the matches are
  suppressed (in-quotes, in-prose, outside tail window), leaving a
  single line of unquoted continuation prose that still false-
  positives — net effect: tuned logic is strictly better but the
  documented false-positive remains.

- **`negative-halt-in-prompt-scrollback.txt`** (D11v4 NEW) — The
  fixture top (lines 1–24) renders the /goal directive verbatim with
  the markdown-quote prefix (`>` plus space) that the spawned tmux session uses
  when claude echoes the prompt back. The directive prose contains
  nearly every HALT trigger substring as instructional content
  (`intent_gap loopback — DO NOT auto-resolve. HALT and surface`,
  `VCS dirty / wrong branch — DO NOT auto-resolve. HALT and surface`,
  `>5 loopbacks on one story — HALT and escalate`, `If the spec is
  internally inconsistent, surface bad_spec and HALT`, etc). The
  spawned session below the prompt does a healthy story execution
  ending with `STORY_7-2_DONE` and `Status: done`. Under naive
  substring matching this fires HALT on every prompt-prose match
  (the canonical Deviation-#7 failure mode). Under D11v4 tuned
  logic: the tail-window guard suppresses matches outside the last
  60 lines (file is 85 lines; tail starts at line 26 — most prompt-
  prose matches sit at lines 11–23 and are eliminated); the prose-
  suppression guard catches the one prompt-prose match that does
  fall in the tail window (line 33 begins with `>` markdown-quote
  prefix AND with the conditional `If`). **Classification under naive
  rule: HALT (false-positive).** **Classification under D11v4 tuned
  rule: NOT-HALT (correctly).** Net effect: this is the canonical
  fixture demonstrating that the D11v4 guards close Deviation #7's
  false-positive class.

## Structured sidecar fixtures

Tasks T1+T2 of the `bmad-auto-halt-sidecar` build introduced a
sidecar-primary / grep-fallback split to Stage 3.4. Directive #8 in
`skills/bmad-auto/references/autonomous-mode-directives.md` instructs
the spawned per-story `claude` agent to write a structured JSON sidecar
to `_bmad-output/.run-state/quick-dev-halt-<storyId>.json` BEFORE
exiting on any HALT-class condition. SKILL.md Stage 3.4 reads that
sidecar as the **definitive** HALT signal when it is present-and-valid;
when the sidecar is absent or malformed (invalid JSON, or valid JSON
missing a required field), Stage 3.4 falls back gracefully to the
existing capture-pane grep heuristic exercised by the `trigger-*.txt` /
`negative-*.txt` fixtures above. Stage 4.e digest composition prefers
the sidecar's `reason` + `files_affected` when the sidecar fired and
otherwise composes from the capture-pane tail.

The fixtures in this section are reference exemplars for that
sidecar-primary code path. They complement (do not replace) the
capture-pane fixtures inventoried above — both paths must continue
to work, since the grep fallback is what fires when an older quick-
dev runtime, an OOM-killed agent, or a half-written file leaves the
sidecar absent or malformed.

### Sidecar fixture inventory

| Fixture | Expected | Notes |
| --- | --- | --- |
| `sidecar-intent-gap.json` | **HALT** (definitive via sidecar) | `status: "intent_gap"`. Realistic AC-3 divergence between a tiered-window acceptance criterion (story `K-3-tiered-window`) and the flat-window implementation primitive in `src/rate_limit/window.ts`. `iteration: 2`, 4 files in `files_affected`. Schema-conformant. |
| `sidecar-bad-spec.json` | **HALT** (definitive via sidecar) | `status: "bad_spec"`. Realistic internally-inconsistent spec for story `5-2-export-csv`: AC-1 (stream rows, memory ceiling) contradicts AC-4 (global sort across full result set), plus a missing-helper reference. `iteration: null` (fires before iteration starts), empty `files_affected`. Schema-conformant. |
| `sidecar-red-tests-failing.json` | **HALT** (definitive via sidecar) | `status: "red_tests_failing"`. Covers the v4 NEW trigger from D1v4 — ATDD authored 4 red tests for story `4-3-quota-reset`; quick-dev drove 2 of 4 green but AC-3 (boundary race) and AC-Ops (clock-skew) remained red at iteration 5 budget exhaustion. `iteration: 5`, 4 implementation paths in `files_affected`. Schema-conformant. |
| `negative-sidecar-malformed.json` | **NOT-HALT** (graceful fallback to grep) | Invalid JSON — truncated mid-string with no closing brace, simulating an agent killed mid-`fwrite`. Under SKILL.md Stage 3.4 the parse failure causes the sidecar to be treated identically to sidecar-absent: fall back to the capture-pane grep heuristic. **The malformed sidecar is NOT itself a HALT** — a parse error must not corrupt orchestration. |

### Sidecar-path classification (asserted by `test_halt_check_sidecar.py`)

This section was originally a desk-check walkthrough of the sidecar-
primary code path against the SKILL.md Stage 3.4 prose; post-v5 the
same classifications are asserted in code by
`skills/bmad-auto/scripts/tests/test_halt_check_sidecar.py`. The walk-
through reading remains useful as the per-fixture expected-outcome
narrative:

1. **Read directive #8.** Open
   `skills/bmad-auto/references/autonomous-mode-directives.md` and
   confirm the schema fields are: `status` (one of
   `intent_gap | bad_spec | loopback_overflow | vcs_dirty | wrong_branch | halt | red_tests_failing`),
   `reason` (string), `iteration` (integer or `null`),
   `files_affected` (array of paths), `timestamp` (UTC ISO 8601),
   `storyId` (string). If the schema has changed since this README
   was written, the fixtures and this table need updating.
2. **For each `sidecar-<status>.json` trigger fixture:**
   - Parse the JSON. Expected: parses cleanly.
   - Confirm all six required fields are present and `status` is in
     the published enum.
   - Classify: under Stage 3.4 the present-and-valid sidecar is the
     **definitive HALT signal** for that story. The orchestrator
     does NOT also need to grep the capture-pane to confirm; the
     sidecar is authoritative when valid. Digest composition (Stage
     4.e) takes `reason` + `files_affected` directly from the JSON.
3. **For `negative-sidecar-malformed.json`:**
   - Attempt to parse the JSON. Expected: parse failure (truncated
     mid-string, no closing brace).
   - Under Stage 3.4 the parse failure is treated identically to
     sidecar-absent: the orchestrator falls back to the
     capture-pane grep heuristic for that poll cycle. If the
     capture-pane has a HALT trigger substring, the run HALTs via
     the legacy path; if not, the run continues polling normally.
   - **Critical edge case:** the malformed sidecar must NOT itself
     fire HALT. A parse error is an inability to read the primary
     signal, not the primary signal saying "HALT". Treating
     malformed-as-HALT would let any agent crash-mid-write
     spuriously halt a healthy story.

### Cross-references

- **T1 — producer side:** directive #8 in
  `skills/bmad-auto/references/autonomous-mode-directives.md` is what
  instructs the spawned per-story `claude` agent to write these
  sidecars at runtime. The fixtures in this section are reference
  exemplars of what conformant runtime output looks like.
- **T2 — consumer side:** SKILL.md Stage 3.4 (per-story poll loop —
  now implemented in `check_halt` / `cmd_monitor` inside
  `skills/bmad-auto/scripts/bmad-auto-helper.py` post-v5) reads the
  sidecar as primary HALT signal; Stage 4.e composes the digest
  preferentially from sidecar fields. The malformed-fallback branch
  (exercised by `test_halt_check_sidecar.py::test_sidecar_malformed_falls_through`)
  is what makes `negative-sidecar-malformed.json` resolve to
  graceful-fallback rather than HALT.
- **Existing inventory above:** the `trigger-*.txt` /
  `negative-*.txt` capture-pane fixtures remain the verification
  surface for the grep-fallback path. The sidecar fixtures
  **complement** them — both surfaces must keep working since the
  fallback fires on older runtimes, OOM kills mid-write, and any
  case directive #8 isn't honoured.

## How the helper consumes these

Post-v5, the executable HALT-detection logic lives in the stdlib-only
helper at `skills/bmad-auto/scripts/bmad-auto-helper.py`, and these
fixtures are wired in as inputs to the helper's pytest suite at
`skills/bmad-auto/scripts/tests/`. Run the suite from the repo root:

```sh
python3 -m pytest skills/bmad-auto/scripts/tests/ -v
```

Three test files in particular consume this directory:

1. **`test_halt_check_grep.py`** — exercises the capture-pane grep
   fallback path of `check_halt` against the `trigger-*.txt` and
   `negative-*.txt` fixtures. Each fixture's expected classification
   from the table above maps to one test:
   - The 7 positive trigger fixtures each assert
     `result["halt"] is True` and pin the expected `class` (e.g.
     `intent_gap`, `bad_spec`, `vcs_dirty`, `wrong_branch`,
     `loopback_overflow`, `halt_literal`, `red_tests_failing`).
   - The 3 clean-negative fixtures (`negative-clean-progress.txt`,
     `negative-loopback-count-2.txt`,
     `negative-halt-in-prompt-scrollback.txt`) assert
     `result["halt"] is False`.
   - The 4 documented-heuristic-limitation fixtures
     (`negative-branch-discussion.txt`,
     `negative-intent-gap-resolved.txt`,
     `negative-mention-of-halt-in-spec.txt`,
     `negative-red-tests-discussion.txt`) assert
     `result["halt"] is True` — pinning the documented false-positive
     under the current substring-with-3-guards heuristic. **These are
     regression baselines, not defects** (see "Ambiguity flags"
     below and "Heuristic limitation regression baselines"
     reiteration below).
2. **`test_halt_check_sidecar.py`** — exercises the sidecar-primary
   path of `check_halt` against the `sidecar-*.json` fixtures. The
   three positive sidecar fixtures assert halt-via-sidecar with the
   expected `class`; `negative-sidecar-malformed.json` asserts
   graceful fall-through to grep.
3. **`test_monitor_*.py`** — exercises the four `cmd_monitor` outcome
   classes (`completed`, `halted`, `stalled`, `timeout`) using the
   sidecar and capture-pane fixtures as staged poll-cycle inputs.

The fixtures are read via the `fixtures_dir` pytest fixture (defined
in `skills/bmad-auto/scripts/tests/conftest.py`) and piped through a
patched `helper.run_tmux` so the production code path runs unmodified.

### Heuristic limitation regression baselines — do not "fix"

The 4 negative fixtures in the documented-limitation bucket
(`negative-branch-discussion.txt`,
`negative-intent-gap-resolved.txt`,
`negative-mention-of-halt-in-spec.txt`,
`negative-red-tests-discussion.txt`) intentionally false-positive
under the current substring-with-3-guards heuristic, and the pytest
suite asserts the false-positive outcome on purpose. They exist to
catch silent regressions in the heuristic (and to pin a diff baseline
for any future semantic upgrade). Per the "conservative wins" posture
documented above, treating these as HALT is the chosen project
posture — see the "Ambiguity flags (summary, for D11v4's intake)"
section below for the per-fixture rationale.

### Optional: shell-based smoke test of the raw substring set

The pytest suite is the authoritative verification path. As an
ad-hoc sanity probe against the raw substring set (useful when
auditing whether a new fixture matches the documented triggers at
all), from the project root:

```
for f in skills/bmad-auto/test-fixtures/halt-detection/trigger-*.txt; do
  echo "=== $f ==="
  grep -iE 'intent_gap|bad_spec|VCS dirty|wrong branch|>5 loopbacks|more than 5 loopbacks|loopback ceiling|HALT|red tests still failing|tests not green' "$f" || echo "NO MATCH (regression!)"
done

for f in skills/bmad-auto/test-fixtures/halt-detection/negative-*.txt; do
  echo "=== $f ==="
  grep -iEn 'intent_gap|bad_spec|VCS dirty|wrong branch|>5 loopbacks|more than 5 loopbacks|loopback ceiling|HALT|red tests still failing|tests not green' "$f" || echo "NO MATCH (clean negative)"
done
```

This is the naive-matcher behavior (no guards applied) — the
fixtures listed under "Ambiguity flag: yes" will produce matches,
which is the point. The pytest suite then layers the guards on top
and asserts the post-guard outcome.

## Ambiguity flags (summary, for D11v4's intake)

Four fixtures are pre-staged false-positive risks. D11v4 should treat
these as the design-validation cases when tuning the parser:

1. **`negative-branch-discussion.txt`** — knife-edge on the `HALT`-
   literal discrimination rule. The substring `HALT` appears once in
   English-prose context. The current SKILL.md rule already says this
   should NOT match; the question for D11v4 is whether the implemented
   parser correctly applies the rule.
2. **`negative-intent-gap-resolved.txt`** — knife-edge on the
   "current event vs. historical recap" distinction. The substring
   `intent_gap` appears in a resumption preamble describing a
   *resolved* prior halt. The current heuristic has no signal for
   resolved-vs-current; conservative-wins says treat as HALT.
3. **`negative-mention-of-halt-in-spec.txt`** — catastrophic case for
   any story whose subject matter IS the HALT-detection logic. The
   only structural feature distinguishing it from real HALTs is that
   the substrings appear inside spec quotations and prose, not as
   surfaced status lines. The current heuristic cannot distinguish
   the two.
4. **`negative-red-tests-discussion.txt`** (v4 NEW) — methodology-
   prose analog of #3 specifically for the new tests-first trigger.
   `red tests still failing` and `tests not green` appear inside
   documentation prose describing what the trigger means; the actual
   doctest run is fully green at exit. Same shape as #3 but applied
   to the v4-introduced trigger class. Discrimination needs likely
   share an implementation with the resolved-vs-current handling
   from #2.

D11v4 took option (b) — added structural discrimination via three
guards (tail-window scoping, prose-line suppression, retained HALT-
literal discrimination) plus an orthogonal STALL outcome class for
the silent-no-progress mode. Documented false-positives in #2/#3/#4
above still trip under tuned logic (conservative-wins accepts them);
the new Deviation-#7-class false-positive (prompt-prose scrollback)
is closed by the tail-window + prose-suppression combination —
demonstrated by `negative-halt-in-prompt-scrollback.txt`.

## D11v4 outcome class additions

The HALT-detection logic now produces three mutually exclusive
outcomes per poll, detected in this order:

1. **`done`** — sprint-status.yaml story key flipped to `done`.
   Authoritative terminal signal. Printed string markers in the
   capture-pane are advisory-secondary only.
2. **`HALT`** — a HALT trigger substring matched in the capture-
   pane AND passed all three structural guards (tail-window,
   prose-line suppression, HALT-literal discrimination). Operator
   inspects halt-context.txt and either re-runs or course-corrects.
3. **`stalled`** — new D11v4 outcome. Fires when ALL of: 3
   consecutive identical capture-pane fingerprints, sprint-status
   not done, no HALT triggered, story has been running ≥5 minutes.
   Surfaces to operator without auto-killing the session (operator
   may want to attach and nudge it).

A poll producing none of the three = "still running, continue polling".

## Fixture count summary

- **Trigger fixtures (positive):** 8 + 3 sidecar = 11
  - v3: `trigger-intent-gap.txt`, `trigger-vcs-dirty.txt`,
    `trigger-wrong-branch.txt`, `trigger-loopback-overflow.txt`,
    `trigger-explicit-halt.txt`
  - v4 NEW: `trigger-red-tests-failing.txt`
  - D11v4 NEW (STALL outcome): `trigger-stall-no-terminal-marker.txt`
  - README-follow-up NEW (2026-05-26): `trigger-bad-spec.txt`
  - T3 NEW (sidecar-primary path): `sidecar-intent-gap.json`,
    `sidecar-bad-spec.json`, `sidecar-red-tests-failing.json`
- **Negative fixtures (adversarial):** 7 + 1 sidecar = 8
  - v3: `negative-clean-progress.txt`, `negative-loopback-count-2.txt`,
    `negative-branch-discussion.txt`, `negative-intent-gap-resolved.txt`,
    `negative-mention-of-halt-in-spec.txt`
  - v4 NEW: `negative-red-tests-discussion.txt`
  - D11v4 NEW: `negative-halt-in-prompt-scrollback.txt`
  - T3 NEW (sidecar malformed-fallback): `negative-sidecar-malformed.json`

**Total fixtures: 19 (15 capture-pane + 4 sidecar).**

**Trigger-class coverage vs SKILL.md Stage 3.4:**

- All 7 substring trigger classes now have a dedicated positive
  fixture. The previously-flagged `bad_spec` coverage gap (D1v4,
  deferred out of D11v4 scope) is closed by `trigger-bad-spec.txt`
  (README-follow-up, 2026-05-26). The capture-pane fixture pairs
  with the existing `sidecar-bad-spec.json` exemplar — same story
  (5-2-export-csv), same scenario (AC-1 streaming vs AC-4 global
  sort contradiction + missing `paginated_query()` helper), so the
  grep-fallback and sidecar-primary paths share one internally-
  consistent narrative.
- The new STALL outcome class has its first positive fixture
  (`trigger-stall-no-terminal-marker.txt`) via D11v4.
