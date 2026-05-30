# Digest dry-render fixtures

Hand-crafted sidecar inputs + expected rendered digests that exercise
SKILL.md stage 7.3 ("End-of-run digest + reminders") composition without
actually running `bmad-auto`. The point is to walk SKILL.md against
concrete inputs and confirm the one-screen claim holds on both the
natural-exit and HALT-exit paths.

## Source SKILL.md stage

All assertions in this directory map to SKILL.md
`skills/bmad-auto/SKILL.md` § 7.3:

- 7.3.1 — runId resolution from orchestrator-session memory
- 7.3.2 — sidecar inputs the digest reads (this directory's mock files
  match those filenames literally)
- 7.3.3 — implied HALT-vs-natural branching (the branch points are
  in 7.3.5's body)
- 7.3.4 — next-backlog-epic lookup against `sprint-status.yaml`
- 7.3.5 — canonical digest composition layout (the structure of
  `expected-digest.md` in each scenario)
- 7.3.6 — terminal print + file save (one digest body, two surfaces;
  the file we ship here is what both surfaces render byte-for-byte)
- 7.3.7 — clean exit (no follow-up tool calls)

Cross-references: 7.1 (Codex outputs the digest links to), 7.2
(deferred-work delta outputs the digest counts come from).

## Scenarios

`K = 3` in both scenarios. The "next backlog epic" lookup at 7.3.4
should resolve to `4` in both.

### natural-exit/

Models a clean dev run where every non-tracer story in epic 3 reached
`status: done`. Codex review fired, deferred-work delta was computed,
and the digest renders the full canonical layout including counts and
the codex-review file link.

Mock sidecars present:

- `epic-K-start.sha` — placeholder SHA (`abc1234…`)
- `epic-K-end.sha` — placeholder SHA (`def4567…`)
- `codex-available.txt` — `true`
- `deferred-work-start.snapshot` — `lines:42 sha:0123…`
- `epic-K-deferred-delta.md` — realistic delta with 2 scope-split, 3
  review-finding, 1 ambiguous entries (counts drawn from D2's
  classifier fixtures and reshaped through SKILL.md 7.2.6's structure)
- `epic-K-codex-review.md` — ~35-line placeholder Codex review with
  the header / diff range / invocation / integration-drift /
  cross-story / missed-AC body that 7.1.5 prescribes
- `sprint-status.yaml` — epic 3 (4 stories) all `done`; epic 4
  backlog (next-backlog-epic target); epic 5 backlog
- `expected-digest.md` — the rendered digest from 7.3.5

### halt-exit/

Models a HALTed run that stopped mid-loop at story 3-3 on an
`intent_gap`. Codex review and deferred-work delta are skipped per the
HALT-skip guards in 7.1.1 and 7.2.1. The digest still fires (7.3
explicit: "fires regardless"), but with the HALT-flavored variations:
`Status: HALTED at story 3-3`, codex/deferred-delta skip lines, a
HALT-context block inlined verbatim from the capture-pane sidecar, and
the retrospective parenthetical modified to flag the skip.

Mock sidecars present:

- `epic-K-start.sha` — same placeholder as natural-exit
- `epic-K-end.sha` — different placeholder (`7777eee…`); per SKILL.md
  7.3.2 this is captured at digest time on HALT runs without
  `--per-story-codex`, since Reconcile 7.1.3 only writes
  `epic-K-end.sha` on the natural-exit branch
- `codex-available.txt` — `true` (codex was available; HALT itself is
  what skipped the review)
- `deferred-work-start.snapshot` — same placeholder as natural-exit
- `epic-K-halt-context.txt` — ~14-line capture-pane excerpt
  inheriting the substance of
  `skills/bmad-auto/test-fixtures/halt-detection/trigger-intent-gap.txt`
  (D1's intent-gap fixture). Trimmed from the full 30+ lines that
  capture-pane would emit so the rendered digest can fit the
  one-screen claim; see "SKILL.md-vs-rendered deviations" below.
- `sprint-status.yaml` — epic 3 partial (3-1 + 3-2 done, 3-3
  `in-progress`, 3-4 `ready-for-dev`); epic 4 backlog; epic 5 backlog
- `expected-digest.md` — the rendered HALT-exit digest

Sidecars **deliberately omitted** in halt-exit/ (and the reason):

- `epic-K-codex-review.md` — 7.1.1's HALT-skip guard means Reconcile
  7.1 short-circuits before invoking codex, so no file is produced.
  The digest renders `Skipped — launch halted at story 3-3` directly
  from orchestrator-memory's one-line note.
- `epic-K-deferred-delta.md` — 7.2.1's HALT-skip guard means
  Reconcile 7.2 short-circuits before computing the delta, so no
  file is produced. The digest renders `Skipped — launch halted at
  story 3-3` directly.
- `epic-K-codex-skipped.txt` — SKILL.md 7.1.1 says explicitly: "Do
  not write `epic-K-codex-skipped.txt` for this case — that sidecar
  is reserved for the codex-unavailable case in step 1.2 below." The
  HALT-skip note reaches the digest via orchestrator-memory, not via
  a sidecar file.

## Verification checklist

The criteria below are the D5 verification items from
`bmad-auto-validate.md`. Pass/fail call follows each.

### natural-exit

| # | Criterion | Source | Actual | Verdict |
|---|---|---|---|---|
| 1 | Digest ≤ ~35 terminal lines | one-screen claim | 31 lines | PASS |
| 2 | All sections from 7.3.5 present | 7.3.5 layout | h1 title, Epic, Status, Duration, Mode, Stories completed (+ list), Diff range, Tracer doc line, Codex review, Deferred-work delta, Codex billing, Next steps block (3 reminders) — all present | PASS |
| 3 | `Status: Completed naturally` | 7.3.5 note | Present on line 4 | PASS |
| 4 | Codex link surfaces | 7.3.5 layout | `Saved to _bmad-output/implementation-artifacts/epic-3-codex-review.md` | PASS |
| 5 | Deferred-work counts inline | 7.3.5 layout | `Scope-split: 2 \| Review-finding: 3 \| Ambiguous: 1 \| Total: 6` | PASS |
| 6 | Next-backlog-epic lookup right | 7.3.4 | Epic 4 (lowest backlog > 3) selected; third reminder reads `→ /bmad-auto --prep --epics 4` | PASS |
| 7 | Retrospective parenthetical natural-flavored | 7.3.5 note | `(Discuss: 6 deferred items added)` | PASS |

### halt-exit

| # | Criterion | Source | Actual | Verdict |
|---|---|---|---|---|
| 1 | Digest ≤ ~45 terminal lines | one-screen claim | 45 lines | PASS (at ceiling — see deviations) |
| 2 | `Status: HALTED at story <id>` | 7.3.5 note | Line 4: `Status: HALTED at story 3-3` | PASS |
| 3 | Codex link skipped | 7.3.5 HALT branch | `Codex review: Skipped — launch halted at story 3-3` | PASS |
| 4 | Deferred-work counts skipped | 7.3.5 HALT branch | `Deferred-work delta: Skipped — launch halted at story 3-3` | PASS |
| 5 | HALT context block included | 7.3.5 HALT-only render | 14-line block headed `HALT context (last lines from the halted tmux session):`, body indented 4 spaces verbatim from sidecar | PASS |
| 6 | Retrospective parenthetical HALT-flavored | 7.3.5 note | `(Discuss: HALT exit — deferred-work analysis skipped)` | PASS |
| 7 | Next-backlog-epic lookup preserved | 7.3.4 | Epic 4 still selected (HALT in epic 3 does not block epic 4); third reminder reads `→ /bmad-auto --prep --epics 4` | PASS |
| 8 | Stories completed excludes halted story | 7.3.5 note | Count = 2 (3-1-tracer, 3-2-add-rate-limiter). 3-3 NOT counted because it HALTed, not finished. | PASS |

## SKILL.md-vs-rendered deviations (G1 intake)

1. **HALT-context length tension with one-screen claim.** SKILL.md
   5.2.9.2 captures the last ~50 lines of the halted tmux session into
   `epic-K-halt-context.txt`. SKILL.md 7.3.5 says inline that file
   "verbatim" with a 4-space indent. SKILL.md 7.3.5 *also* says the
   digest should be ~40–50 lines. A 50-line halt context block alone
   blows past the one-screen budget even before the digest's other
   sections are counted.

   This dry-render trims the halt context to ~14 lines (the most
   diagnostic excerpt) to land at 45 lines total. With the full
   ~50-line capture-pane content, the rendered HALT-exit digest would
   come in at ~85 lines — almost 2x the one-screen claim.

   Recommendation for G1 to consider routing into Phase-3 work:
   either (a) trim `epic-K-halt-context.txt` at write time in 5.2.9.2
   (e.g. `tail -n 20`), (b) have the digest itself emit only the last
   N lines of the sidecar with a `(see full halt context at
   <path>)` link, or (c) loosen the one-screen claim for HALT runs
   and accept ~70 lines as the "still scannable" upper bound for HALT
   exits specifically. Option (b) preserves byte-for-byte
   identicality between terminal and saved file most cleanly.

2. **`epic-K-end.sha` provenance ambiguity on HALT runs.** SKILL.md
   7.3.2 says: if `epic-K-end.sha` is "absent because of HALT exit,
   derive from the last
   `_bmad-output/.run-state/epic-K-story-<storyId>-end.sha` file
   present in the run-state directory (Launch 5.2.11.1.1 writes one
   per completed story on the `--per-story-codex` path; on HALT runs
   without `--per-story-codex` no per-story end-sha exists and we
   fall back to a fresh `git rev-parse HEAD` with a note in the
   digest that the end SHA was captured at digest time, not at
   story-completion time)."

   The "note in the digest" is described but no rendered shape is
   given for it. This dry-render's HALT-exit digest does NOT render
   that note — the prose contract is loose enough that there is no
   one canonical surface to verify against. Recommend codifying the
   note's exact wording in 7.3.5's layout (e.g. a third line under
   `Diff range:` reading `(end SHA captured at digest time, not at
   story-completion time)`) so future renders are deterministic.

3. **The Tracer doc line's "(Format A)" prefix vs. the file path.**
   SKILL.md 7.3.3 specifies the wording *"Tracer (Format A):
   epic-K-micro-prd.md, epic-K-micro-architecture.md"*. The two file
   basenames have no path prefix, while every other file reference in
   the digest (codex review, deferred delta, deferred-work source
   log) uses a full `_bmad-output/...` relative path. Minor
   inconsistency; not a correctness issue, but the operator
   navigating from terminal to file may not realize the tracer docs
   live under `_bmad-output/implementation-artifacts/`. Recommend
   making the tracer line's paths fully qualified for consistency
   with the rest of the digest's file references.

None of the above three are correctness bugs in the dry-render
itself — they are tensions in SKILL.md 7.3's prose that this exercise
surfaced. Phase-3 D-tasks (D6/D7/D8/D9) do not directly cover digest
composition, but G1 may route this back as a D-task addition or a
SKILL.md surgical patch.

## Re-verification protocol (future operator)

To re-verify this dry-render against a future SKILL.md:

1. Re-read SKILL.md `skills/bmad-auto/SKILL.md` § 7.3 entirely; pay
   particular attention to 7.3.2 (sidecar list), 7.3.4 (next-epic
   lookup), and 7.3.5 (composition layout).
2. For each scenario sub-directory:
   - Confirm every file in 7.3.2's sidecar list is either present in
     the directory OR explicitly noted as "deliberately omitted" in
     this README (with a reason that matches a 7.x skip guard).
   - Walk 7.3.5's layout top-to-bottom against the
     `expected-digest.md` file. Every named field/section in 7.3.5
     should appear, in order, with the literal labels the SKILL.md
     text specifies (`Epic:`, `Status:`, `Duration:`, `Mode:`,
     `Stories completed:`, `Diff range:`, `Tracer (Format ...):`,
     `Codex review:`, `Deferred-work delta:`, `Codex billing:`,
     `Next steps:`).
   - For the HALT scenario, confirm the HALT-context block is
     present, the codex / deferred sections show their skip-lines,
     the retrospective parenthetical is the HALT-flavored variant,
     and the halted story is NOT in the stories-completed list.
3. Re-run `wc -l` against each `expected-digest.md` and compare
   against the verification checklist's "Actual" cells. Update this
   README if SKILL.md's one-screen claim or rendered shape has
   shifted.
4. If SKILL.md has been edited to address any of the three
   deviations flagged above, mark the deviation Resolved in this
   README and confirm the rendered digest matches the updated prose.

The fixtures here are deliberately self-contained (no path
references to `_bmad-output/` paths that must actually exist) — they
are inputs to a paper-walk, not artifacts of a real run. Do not
mistake them for run output.

## Not in scope for D5

- Real `<runId>` generation. The placeholder `20260525T120000Z` is
  treated as ground truth; SKILL.md 5.1.3's `date -u +%Y%m%dT%H%M%SZ`
  bash invocation is not exercised here.
- Real SHA generation. Placeholders are used throughout; SKILL.md
  5.1.1's `git rev-parse HEAD` is not exercised.
- Actually invoking the skill. D5 is composition verification only,
  per the picker note in `bmad-auto-validate.md`.
- Codex / deferred-classifier correctness on their own. D2 and D3
  cover those surfaces; D5 only verifies that whatever they produce
  gets faithfully surfaced by the digest.

---

## v4 scenarios (D5v4 extensions)

The original `natural-exit/` and `halt-exit/` scenarios above remain
valid for the v3 digest layout that SKILL.md `§ 7.3` describes. v4
SKILL.md re-homed the digest into `§ Stage 4.e` and added three new
sections to the canonical composition:

- **Quality gates** (Trace + NFR verdicts from Stage 4.a / 4.b)
- **Spike triage** (per-epic spike-log summary from Stage 1.f)
- **Retrospective signals** (significant-discoveries +
  critical-readiness flags from Stage 4.f)

The four v4 scenarios below sit alongside the v3 scenarios and
exercise the new sections. They follow the same conventions (each
scenario sub-directory is a self-contained set of sidecar inputs +
the rendered `expected-digest.md`), with the deliberate v4 deviations
noted later in this section.

### natural-exit-v4/

The v4 "happy path". Express mode, epic 3 with 3 stories (K-1
tracer, K-2, K-3), all `done`, all gates PASS, retrospective ran
with no critical signals, no spike-triage entries. Demonstrates the
full v4 canonical layout in its simplest form.

- Budget target: 50 lines. Actual: **34 lines**.
- New v4 sections present: Quality gates (lines 8–10), Spike triage
  (line 19), Retrospective signal (lines 29–30).

### quality-gate-fail/

Trace=CONCERNS + NFR=FAIL → combined verdict `BLOCK`. Models the
case where the dev run completed but quality gates surfaced
mergeability issues. Retrospective ran (4.f only skips on HALT)
and recorded `critical_readiness=FAIL` because the gates blocked.

- Budget target: 50 lines. Actual: **40 lines**.
- BLOCK verdict surfaced as a stand-alone token on the Quality
  gates header line (line 8) so an operator scanning the digest sees
  the verdict before reading sub-gate details.

### quality-gate-waived/

Trace=WAIVED with a one-line rationale ("tracer-only coverage
acceptable for this internal tool — no external API surface,
single-tenant deployment"), NFR=PASS. Combined verdict `PROCEED
(with documented risk)`. The waiver rationale appears twice in the
digest: once inline with the trace gate, and once as a "decision log
entry" under Next steps so it lands in merge descriptions.

- Budget target: 50 lines. Actual: **37 lines**.
- Demonstrates that WAIVED is rendered as itself (not laundered into
  a PASS-equivalent).

### headless-exit/

Headless mode, unattended overnight run, default skip of Stage 4.f
retrospective. The digest reads cold: a tired operator opening it
in the morning sees `Mode: Headless`, gates PASS, and an explicit
`Retrospective: Skipped — Headless mode (re-run with
--with-retrospective for interactive retro)` line under Next steps.

- Budget target: 50 lines. Actual: **33 lines**.
- `epic-K-retro-signals.txt` is deliberately omitted from the
  sidecar set — the digest reads the file's absence as "Skipped"
  rather than defaulting to PASS.

## v4 verification checklist

The criteria below extend the per-scenario tables in each v4
sub-directory's README. Each line is desk-checked against the
rendered `expected-digest.md` in the named scenario.

| # | Criterion | natural-exit-v4 | quality-gate-fail | quality-gate-waived | headless-exit |
|---|---|---|---|---|---|
| 1 | Line count within ≤ 50-line budget | 34 (PASS) | 40 (PASS) | 37 (PASS) | 33 (PASS) |
| 2 | Status line present and accurate | PASS | PASS | PASS | PASS |
| 3 | Mode line present and accurate | Express | Express | Express | Headless |
| 4 | Quality gates block present | PASS | PASS | PASS | PASS |
| 5 | Trace gate verdict visible (correct token) | PASS | CONCERNS | WAIVED | PASS |
| 6 | NFR gate verdict visible (correct token) | PASS | FAIL | PASS | PASS |
| 7 | Combined verdict surfaced where non-trivial | n/a (PASS+PASS) | BLOCK (line 8) | PROCEED w/ risk (line 8) | n/a |
| 8 | Codex review link visible | PASS | PASS | PASS | PASS |
| 9 | Deferred-work counts inline | PASS (6 total) | PASS (3 total) | PASS (2 total) | PASS (3 total) |
| 10 | Tracer docs paths fully qualified | PASS | PASS | PASS | PASS |
| 11 | Spike triage summary visible | 0 deferred + 0 blocked | 0 + 0 | 0 + 0 | 0 + 0 |
| 12 | Retrospective signal surfaced correctly | clean (line 29) | critical-readiness FAIL (line 34) | clean (line 31) | Skipped — Headless (line 26) |
| 13 | Next-backlog-epic resolves to 4 | PASS | PASS (with caveat) | PASS | PASS |
| 14 | Cold-read sanity (operator can act from digest alone) | PASS | PASS | PASS | PASS |

### Budget rationale

v3 digests landed at 31 lines (natural exit) / 45 lines (HALT exit).
v4 adds three sections; we expanded the per-digest budget ceiling to
**50 lines** for v4 scenarios to accommodate the new content while
preserving the one-screen claim on a standard 50-row terminal. All
four v4 scenarios came in under this ceiling (33–40 lines), giving
~10 lines of headroom even on the most expansive scenario
(quality-gate-fail). The v3 budget for HALT-exit (45 lines, with
the tail-trim convention from v3 D5 deviation #1) is unchanged; if
a v4 HALT-exit scenario is added later, the recommendation is to
keep the ~15-line halt-context tail-trim and accept a ceiling of
~55–60 lines for that specific case.

### v4 deviations from v3 conventions

1. **Composition layout source.** v3 scenarios point at SKILL.md
   `§ 7.3.5`. v4 scenarios point at SKILL.md `§ Stage 4.e`. Section
   numbering is the underlying change; the verification protocol
   structure is otherwise preserved.
2. **Quality gates as a discrete block.** v3 had no per-gate
   verdict tokens in the digest. v4 surfaces both as a labeled
   block (`Quality gates:` header + two indented sub-lines + a
   `VERDICT:` token on the header line when combined verdict is
   non-trivial). All four v4 scenarios surface gates at the same
   position (immediately under the run-meta block, above Codex
   review).
3. **Spike triage line.** v3 had no spike-log. v4 adds a single
   line (`Spike triage: <N> deferred + <M> blocked`). All four v4
   scenarios show `0 deferred + 0 blocked` — a future
   spike-log-rich scenario could be added under D7v4 if needed.
4. **Retrospective signal surfacing.** v3 had a static
   parenthetical (`Discuss: N deferred items added`). v4 surfaces
   actual `epic-K-retro-signals.txt` contents (significant-
   discoveries + critical-readiness flags), with explicit Stage 4.g
   pointer when critical_readiness is FAIL. Headless renders the
   file's absence as `Skipped — Headless mode`.
5. **Tracer-doc paths fully qualified.** v3 D5 deviation #3 flagged
   the inconsistency between `Tracer (Format A): epic-K-micro-*.md`
   (no path) and the fully-qualified `_bmad-output/...` paths used
   elsewhere. v4 scenarios resolve this proactively by always
   emitting fully-qualified paths under `Tracer docs:`.

### Re-verification protocol for v4 scenarios

Same as v3 (read § Re-verification protocol above), with these
substitutions:

- SKILL.md section reference: `§ Stage 4.e` (not `§ 7.3.5`).
- Sidecar list to verify: includes `epic-K-trace-gate.txt`,
  `epic-K-nfr-gate.txt`, `epic-K-spike-log.md`,
  `epic-K-retro-signals.txt` (the last is deliberately absent in
  `headless-exit/`).
- Composition layout: verify the Quality gates block, the Spike
  triage line, and the Retrospective sub-section under Next steps
  all appear in the order the SKILL.md Stage 4.e canonical layout
  specifies.
