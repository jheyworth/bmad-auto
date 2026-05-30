# Deferred-work classifier fixture suite

Validation fixtures for the deferred-work-entry classification
heuristic in `skills/bmad-auto/SKILL.md`, stage 7 (Reconcile), sub-step
**7.2.5** — "Classify each new entry" inside the end-of-epic
deferred-work delta computation.

Each fixture is a realistic `deferred-work.md` **entry** (one entry,
not a full file) of the kind quick-dev appends after a Step 1 / Step 2
scope-split or a Step 4 reviewer-defer. The fixtures exercise every
classification outcome the heuristic can produce.

## Source-of-truth (verbatim from SKILL.md 7.2.5)

> **scope-split markers** (derived from quick-dev Step 1 §4 multi-goal
> check and Step 2 §6 token-count split — both append `deferred goals`
> after the operator picks `[S] Split`):
>
> - `deferred goal` / `deferred goals`
> - `secondary goal` / `secondary goals` (Step 2 uses this when
>   proposing the split)
> - `split:` or `split —` near the start of the entry
> - `narrow scope` / `narrowed scope`
> - The literal token `[S]` or `[S] Split`
>
> **review-finding markers** (derived from quick-dev Step 4 § Classify
> line 45 — `**defer** — Append to {deferred_work_file}` — and
> `step-oneshot.md` line 29 — `**defer** — pre-existing issue not
> caused by this change`):
>
> - `pre-existing issue` (the most diagnostic phrase — Step 4 and
>   one-shot both lean on it)
> - `not caused by this change` / `not caused by this story`
> - `review finding` / `review-finding`
> - The literal token `defer` or `**defer**` paired with reviewer-
>   classification language (look for `intent_gap`, `bad_spec`,
>   `patch`, `reject` nearby — these are the cascading categories from
>   Step 4 §3 that travel together in reviewer context).
> - `blind hunter` / `edge case hunter` / `acceptance auditor` (the
>   three Step 4 reviewer roles, listed verbatim in step-04-review.md
>   lines 28–30 — if the reviewer named themselves, this is a
>   review-finding)
>
> **Classification logic:**
> - If exactly one marker family matches → classify accordingly.
> - If both families match in one entry → prefer `review-finding`
>   (Step 4 / one-shot review-driven defers are the more common path
>   in autonomous mode where Step 1's multi-goal check defaults to
>   `[K] Keep all goals` per `references/autonomous-mode-directives.md`
>   directive #2). Add a `(both markers matched — defaulted to
>   review-finding)` note in the saved entry.
> - If no markers match → classify as `ambiguous` and surface in the
>   dedicated section per the picker note default-to-review-finding
>   rule. The saved file MUST count ambiguous entries separately (not
>   silently roll them into review-finding) so the operator can refine
>   classifier rules later. Each ambiguous entry gets the inline note
>   `matched neither marker — review classifier rules`.

the helper halt-detection notes § "Known limitations" confirms this is heuristic by
design. The build-task list `bmad-auto.md` D9 Outcome
documents the **critical finding**: quick-dev does NOT emit a
structured per-entry format when appending to `deferred-work.md`. The
classifier markers above are inferred from quick-dev's source-code
language describing the defer action, not from anything quick-dev
explicitly writes into the file. Classification accuracy is therefore
best-effort, and the `Ambiguous entries` section is the relief valve.

## Marker source language in quick-dev (cross-reference)

D9's Outcome traced the marker phrases back to specific lines in
quick-dev source. The fixtures in this suite mirror that language so
re-verification against the source is straightforward.

| Marker family | Source file (quick-dev) | Source line(s) | Source quote |
| --- | --- | --- | --- |
| scope-split | `BMAD-METHOD/src/bmm-skills/4-implementation/bmad-quick-dev/step-01-clarify-and-route.md` | 84–85 | "HALT and ask human: `[S] Split — pick first goal, defer the rest` \| `[K] Keep all goals — accept the risks`" / "On **S**: Append deferred goals to `{deferred_work_file}`. Narrow scope to the first-mentioned goal." |
| scope-split | `BMAD-METHOD/src/bmm-skills/4-implementation/bmad-quick-dev/step-02-plan.md` | 21–22 | "`[S] Split — carve off secondary goals` \| `[K] Keep full spec — accept the risks`" / "Propose the split — name each secondary goal. Append deferred goals to `{deferred_work_file}`. Rewrite the current spec to cover only the main goal … regenerate the spec for the narrowed scope." |
| review-finding | `BMAD-METHOD/src/bmm-skills/4-implementation/bmad-quick-dev/step-04-review.md` | 28–30, 39, 45 | "**Blind hunter**" / "**Edge case hunter**" / "**Acceptance auditor**" (reviewer roles); "**defer** — pre-existing issue not caused by this story, surfaced incidentally by the review"; "**defer** — Append to `{deferred_work_file}`." |
| review-finding | `BMAD-METHOD/src/bmm-skills/4-implementation/bmad-quick-dev/step-oneshot.md` | 29 | "**defer** — pre-existing issue not caused by this change. Append to `{deferred_work_file}`." |
| review-finding (cascading context) | `BMAD-METHOD/src/bmm-skills/4-implementation/bmad-quick-dev/step-04-review.md` | 36–41 | The five cascading categories (`intent_gap`, `bad_spec`, `patch`, `defer`, `reject`) that travel together in reviewer context — `defer` is diagnostic only when one or more of `intent_gap` / `bad_spec` / `patch` / `reject` appears nearby. |

Fixtures use the verbatim phrases from those sources rather than
paraphrases, so the substring match in 7.2.5 fires the same way the
runtime classifier will fire against real quick-dev output.

## Fixture inventory and expected classification

| Fixture | Expected | Driving marker(s) | Notes |
| --- | --- | --- | --- |
| `scope-split-clear.md` | **Scope-Split** | `deferred goal` (x4), `deferred goals` (x2), `[S] Split` (x1), `narrow scope` (x1) | Clean Step-1 split. All three "obvious" scope-split markers fire. No review-finding markers present (per the cascading-context rule, the substring `defer` in `deferred` is not enough on its own — it must be paired with `intent_gap` / `bad_spec` / `patch` / `reject` to count as review-finding). |
| `scope-split-subtle.md` | **Scope-Split** | `split:` (line 9, near the start of the entry per the SKILL.md "near the start" qualifier), `secondary goal` (x2), `narrowed scope` (x1) | Quick-dev's Step 2 §6 token-count split language. Deliberately omits `[S]` and `deferred goal` — exercises the more subtle markers. No review-finding markers. |
| `review-finding-clear.md` | **Review-Finding** | `pre-existing issue` (x2), `not caused by this change` (x1), `not caused by this story` (x1), `Defer` / `defer` paired with the cascading categories (`intent_gap=0`, `bad_spec=0`, `patch=0`, `defer=3`, `reject=2`), `blind hunter` (x2), `edge case hunter` (x3) | Clean Step-4 reviewer pass. All three diagnostic phrases present; two reviewer roles named explicitly. |
| `review-finding-subtle.md` | **Review-Finding** | `defer` (x6) paired with `intent_gap` (x3), `bad_spec` (x2), `patch` (x4), `reject` (x2), `acceptance auditor` (x1), `pre-existing issue` (x1), `not caused by this story's diff` (line 45 — variant of `not caused by this story`) | Reviewer pass that leans on the cascading-category context rather than the diagnostic phrases. Demonstrates that the `defer + cascading` pairing is sufficient even when `pre-existing issue` shows up only once. |
| `both-markers.md` | **Review-Finding** (`both markers matched — defaulted to review-finding`) | scope-split side: `[S] Split` (x1), `deferred goal` (x4), `secondary` (x1); review-finding side: `pre-existing issue` (x2), `not caused by this change` (x1), `blind hunter` (x1), `acceptance auditor` (x1), `defer` paired with cascading-context language | One entry that contains both families. Per SKILL.md 7.2.5 the default is review-finding with the inline note. Real-world plausibility: a single story can both trip the Step-1 multi-goal split AND produce Step-4 defers — quick-dev would append both into the same file in close succession. |
| `no-markers.md` | **Ambiguous** | (none) | Operator-style follow-up note that quick-dev would never write in this exact shape, but which a future quick-dev variant might produce or which a human author might paste in by hand. Contains the word "reviewer" (which does NOT match `review finding` / `review-finding` / any reviewer-role name) and the word "deferred" embedded in `deferred` (which does not match `deferred goal` / `deferred goals`). Lands in the Ambiguous section with the inline note `matched neither marker — review classifier rules`. |

## Desk-check pass (walking SKILL.md 7.2.5 against each fixture)

The desk-check protocol mirrors what stage 7.2.5 does at runtime: read
the entry top-to-bottom, perform case-insensitive substring matching
against the published scope-split set and the published review-finding
set, apply the both-markers / no-markers logic, and assign a final
classification.

### Scope-split fixtures — both unambiguously Scope-Split

- **`scope-split-clear.md`** — `deferred goal` and `deferred goals`
  appear multiple times; `[S] Split` appears verbatim once; `narrow
  scope` appears once. No `pre-existing issue`, no `not caused by this
  change/story`, no `review finding` / `review-finding`, no reviewer-
  role name. The substring `defer` exists as part of `deferred` but
  the `defer + cascading-context` rule says it must be paired with
  `intent_gap` / `bad_spec` / `patch` / `reject` nearby — none of
  those appear. **Classification: Scope-Split.** No ambiguity.

- **`scope-split-subtle.md`** — `split:` appears at line 9, well
  within the "near the start of the entry" qualifier; `secondary goal`
  appears twice; `narrowed scope` appears once at line 7. No
  review-finding markers. **Classification: Scope-Split.** No
  ambiguity. The deliberate omission of `[S]` and `deferred goal(s)`
  tests whether the heuristic actually exercises the secondary marker
  set, not just the most obvious ones.

### Review-finding fixtures — both unambiguously Review-Finding

- **`review-finding-clear.md`** — `pre-existing issue` (x2), `not
  caused by this change` (x1), `not caused by this story` (x1),
  `blind hunter` (x2), `edge case hunter` (x3), and a cascading-
  categories breakdown line that enumerates the five categories
  including `defer=3`. No scope-split markers. **Classification:
  Review-Finding.** No ambiguity.

- **`review-finding-subtle.md`** — `pre-existing issue` appears only
  once (at line 44, as part of "exactly the class of pre-existing
  issue defer is for"), so the entry leans on the cascading-context
  pairing instead. Multiple `defer` tokens appear alongside
  `intent_gap`, `bad_spec`, `patch`, and `reject` — the four
  reviewer-context categories that establish defer-as-review-finding.
  `acceptance auditor` is named once. No scope-split markers.
  **Classification: Review-Finding.** No ambiguity *if* the
  classifier correctly implements the "defer paired with reviewer-
  classification language" rule rather than treating `defer` as a
  stand-alone marker.

### Both-markers fixture — defaulted Review-Finding

- **`both-markers.md`** — both families fire. Scope-split: `[S]
  Split`, `secondary goals`, `deferred goal(s)` (x4 instances).
  Review-finding: `pre-existing issue` (x2), `not caused by this
  change`, `blind hunter`, `acceptance auditor`, `defer` paired with
  cascading-categories context. **Classification under SKILL.md
  7.2.5: Review-Finding with inline note `(both markers matched —
  defaulted to review-finding)`.** The default is correct in spirit
  for the count, but the entry semantically contains real scope-split
  content — see Ambiguity flags below.

### No-markers fixture — Ambiguous

- **`no-markers.md`** — no scope-split marker matches. No review-
  finding marker matches. The closest near-misses are: "reviewer"
  (does not match `review finding` / `review-finding` / any reviewer-
  role name); "deferred" embedded in `deferred` (does not match
  `deferred goal` / `deferred goals` because the heuristic looks for
  the noun-phrase, not the bare past participle); "follow-up"
  (irrelevant). **Classification under SKILL.md 7.2.5: Ambiguous,
  with inline note `matched neither marker — review classifier
  rules`.** The Ambiguous section counts this separately rather than
  silently rolling it into review-finding; the Counts line still adds
  it to the downstream review-finding total per the picker note's
  "default to review-finding and warn" intent.

## Both-marker and no-marker behaviors (summary)

- **Both-markers default = `review-finding`.** Per SKILL.md 7.2.5:
  *"If both families match in one entry → prefer `review-finding`
  (Step 4 / one-shot review-driven defers are the more common path in
  autonomous mode where Step 1's multi-goal check defaults to `[K]
  Keep all goals` per `references/autonomous-mode-directives.md`
  directive #2). Add a `(both markers matched — defaulted to
  review-finding)` note in the saved entry."* The reasoning is that
  autonomous mode rarely produces scope-split entries (because the
  directives default to `[K] Keep all goals`), so when both fire, the
  review-finding intent is the more likely true reading. `both-
  markers.md` exercises this default.

- **No-markers default = `Ambiguous` (counted separately, downstream-
  rolled to review-finding for counts only).** Per SKILL.md 7.2.5:
  *"If no markers match → classify as `ambiguous` and surface in the
  dedicated section per the picker note default-to-review-finding
  rule. The saved file MUST count ambiguous entries separately (not
  silently roll them into review-finding) so the operator can refine
  classifier rules later. Each ambiguous entry gets the inline note
  `matched neither marker — review classifier rules`."* The Counts
  line in `epic-K-deferred-delta.md` renders this as `Ambiguous
  (defaulted to review-finding for downstream count purposes)`.
  `no-markers.md` exercises this default.

## Re-verification protocol

A future subagent or operator can re-walk this desk-check against the
current SKILL.md by following these steps:

1. **Read the source-of-truth.** Open
   `skills/bmad-auto/SKILL.md` and locate stage 7 (Reconcile), sub-
   step 7.2 (end-of-epic deferred-work delta), check 7.2.5 (Classify
   each new entry). Confirm the scope-split marker set and the
   review-finding marker set have not changed since this README was
   written. If they have, the fixtures and the table above need
   updating to mirror the new markers.

2. **Re-check the quick-dev source language.** Open the four quick-
   dev files cross-referenced in the "Marker source language in
   quick-dev" section. Confirm the line numbers and quotes still
   match. Quick-dev source is the substrate the markers were inferred
   from — if quick-dev's defer-action language drifts, the markers
   will drift too, and D7 (classifier marker tuning) may need to
   patch SKILL.md 7.2.5's marker set.

3. **For each fixture file:**
   - Read the fixture top-to-bottom.
   - Apply case-insensitive substring matching against the scope-
     split set. Record matches.
   - Apply case-insensitive substring matching against the review-
     finding set. Record matches. For any `defer` substring, confirm
     whether one or more of `intent_gap` / `bad_spec` / `patch` /
     `reject` appears nearby (within ~5 lines) before counting it.
   - Apply the classification logic: one family → that classification;
     both families → review-finding with note; neither → Ambiguous
     with note.
   - Compare against the table above. Drift means either a fixture
     needs rewriting or the heuristic has changed.

4. **Optional: shell-based smoke test.** From the project root, run
   the naive case-insensitive substring matcher against each fixture
   to see what a literal-rule implementation would produce:

   ```
   for f in skills/bmad-auto/test-fixtures/deferred-classifier/*.md; do
     [ "$(basename "$f")" = "README.md" ] && continue
     echo "=== $f ==="
     echo "-- scope-split markers --"
     grep -iEn 'deferred goal|secondary goal|split:|split —|narrow scope|narrowed scope|\[S\]' "$f" || echo "(none)"
     echo "-- review-finding markers (diagnostic phrases) --"
     grep -iEn 'pre-existing issue|not caused by this change|not caused by this story|review finding|review-finding|blind hunter|edge case hunter|acceptance auditor' "$f" || echo "(none)"
     echo "-- defer + cascading-context --"
     grep -iEn 'defer.*(intent_gap|bad_spec|patch|reject)|(intent_gap|bad_spec|patch|reject).*defer' "$f" || echo "(none)"
   done
   ```

   This is the closest a shell pipeline can get to the SKILL.md rule.
   The third grep is an approximation of the "defer paired with
   reviewer-classification language" qualifier; a real implementation
   would scan a small line-window rather than relying on a single
   line containing both. Mismatches between this smoke test and the
   table above are diagnostic of where the heuristic is on a knife's
   edge.

## Ambiguity flags (for D7's intake)

Two fixtures are pre-staged borderline classifications. D7
(classifier marker tuning) should treat these as the validation cases
when tuning the marker set based on G3 observations.

1. **`both-markers.md`** — knife-edge on the both-markers default.
   The default of `review-finding` is correct as a count-bucketing
   decision (per SKILL.md 7.2.5's reasoning that scope-splits are
   rare in autonomous mode), but the entry semantically contains
   real deferred-goals content that an operator reviewing
   `epic-K-deferred-delta.md` might want to see in the Scope-split
   section. D7 may want to consider whether mixed entries should be
   counted in both buckets (with cross-references), or whether the
   inline note `(both markers matched — defaulted to review-finding)`
   is enough operator-surface to make the default acceptable.

2. **`no-markers.md`** — knife-edge on what "no marker" actually
   means in practice. The fixture is plausibly what quick-dev would
   produce if a future variant added a "captured during
   implementation, not at Step 1 or Step 4" defer path, OR what a
   human operator pasting into `deferred-work.md` by hand would
   write. If G3 observes that real `Ambiguous` entries cluster around
   a small set of recurring phrases (e.g. "follow-up", "documentation
   backlog", "performance backlog"), D7 should consider promoting
   those phrases into the marker set rather than leaving them in the
   Ambiguous relief valve.

The remaining four fixtures (`scope-split-clear.md`, `scope-split-
subtle.md`, `review-finding-clear.md`, `review-finding-subtle.md`)
are designed to be unambiguous and should classify the same way
across any reasonable refinement of the heuristic in D7. If any of
them drifts to a different classification under a future SKILL.md
revision, that is itself a signal that the heuristic has changed
shape and the fixtures need re-validation.

## What's notable

Working through SKILL.md 7.2.5 + D9's Outcome surfaces a key
property of the classification heuristic: it is **asymmetric across
the two families and across the two halves of the review-finding
family itself.** Scope-split markers are direct lexical signals
(`[S] Split`, `deferred goal`, `narrow scope`) that quick-dev emits
verbatim into the file when the operator picks `[S]` at Step 1 / Step
2. Review-finding markers come in two flavors: the **diagnostic
phrases** (`pre-existing issue`, `not caused by this change`,
reviewer-role names) that quick-dev's step-04-review.md and
step-oneshot.md explicitly use; and the **cascading-context pairing**
(`defer` only counts when accompanied by `intent_gap` / `bad_spec` /
`patch` / `reject` nearby), which is necessary because the bare word
`defer` appears too widely in non-review prose to be a reliable
marker on its own. The most diagnostic single phrase is `pre-existing
issue` — Step 4 and one-shot both lean on it, and a future quick-dev
that drops the phrase would degrade the classifier sharply.

The classifier is heuristic by design **because quick-dev does not
emit a structured per-entry format.** Markers are inferred from the
source language quick-dev uses *when describing the defer action*,
not from anything quick-dev *writes into the file*. This means the
heuristic is fundamentally a best-effort match between two
independent surfaces — quick-dev's emission style and the classifier's
marker set — and the `Ambiguous` section exists precisely to absorb
the drift. If a future quick-dev version adds explicit per-entry
headers (e.g. `## [scope-split]` or `## [review-finding] from
blind-hunter`), the heuristic should be revised in favor of
structural matches and most of the markers above can be retired.
Until then, D7's tuning will be incremental marker improvement
guided by what the `Ambiguous` section catches at G3.
