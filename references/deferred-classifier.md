# Deferred-work classifier

> Reference doc used by `/bmad-auto` Stage 4.d to classify entries added
> to `deferred-work.md` during a run. This is the runtime contract the
> agent applies when computing `epic-K-deferred-delta.md`.
>
> Verification fixtures live at
> [`../test-fixtures/deferred-classifier/`](../test-fixtures/deferred-classifier).
> Walk this algorithm against each fixture to verify correctness;
> expected outcomes are documented in the fixture README.

## Classification outcomes

Each new entry in `deferred-work.md` (i.e. entries appended since
`deferred-work-start.snapshot` was captured in Stage 3 setup step 2) is
classified into exactly one of:

| Outcome | When |
| --- | --- |
| **Scope-split** | Step-1 deferred-goal markers present, no review-finding markers |
| **Review-finding** | Review-defer markers present (with or without scope-split markers — review-finding wins on overlap) |
| **Ambiguous** | Neither marker set matches |

The output `epic-K-deferred-delta.md` has one section per outcome plus a
counts summary.

## Markers (verbatim substring matching, case-insensitive)

### Scope-split markers (Step-1 deferred-goal language)

A scope-split classification fires when **any** of these substrings
appears in the entry body:

- `deferred goal` (singular or plural)
- `[S] Split` or the bare literal token `[S]`
- `narrow scope` / `narrowed scope`
- `split:` or `split —` near the start of the entry (when followed by
  a paragraph describing the split)
- `secondary goal` (singular or plural)

### Review-finding markers (Step-4 review-defer language)

A review-finding classification fires when **either**:

**(A) Any diagnostic phrase appears** in the entry body:

- `pre-existing issue`
- `not caused by this change` or `not caused by this story`
- `review finding` / `review-finding`
- `blind hunter`
- `edge case hunter`
- `acceptance auditor`

**OR**

**(B) The cascading-context pairing fires**:

- The word `defer` or `deferred` appears in the entry body, AND
- Within ~5 lines, at least one of: `intent_gap`, `bad_spec`, `patch`,
  `reject` also appears

The cascading-context exists because bare `defer` / `deferred` is too
common in non-review prose to stand alone as a marker.

## Default behavior

| Marker set state | Classification | Inline note in delta entry |
| --- | --- | --- |
| Scope-split only | Scope-split | (none) |
| Review-finding only | Review-finding | (none) |
| **Both present** | **Review-finding** | `(both markers matched — defaulted to review-finding)` |
| **Neither present** | **Ambiguous** | `(matched neither marker — review classifier rules)` |

The both-marker default to `review-finding` is the count-bucketing
convention. The entry semantically may contain real scope-split
content; the inline note flags this for operator audit.

The Ambiguous bucket is the relief valve — operators can audit
borderline cases and tighten the marker list over time (D7 patches in
the validation workstream extend the marker set based on real
observations).

## Algorithm

For each new entry in the delta:

1. **Compute `scope_split_match`:**
   - `true` if any scope-split marker substring appears in the entry body
   - `false` otherwise
2. **Compute `review_match`:**
   - `true` if any diagnostic phrase from set (A) appears, OR
   - `true` if cascading-context pairing (B) fires
   - `false` otherwise
3. **Classify:**
   ```
   if review_match:
       if scope_split_match:
           outcome = review-finding (with both-markers note)
       else:
           outcome = review-finding
   elif scope_split_match:
       outcome = scope-split
   else:
       outcome = Ambiguous (with no-markers note)
   ```
4. **Write to delta file** under the appropriate section.

## Output structure: `epic-K-deferred-delta.md`

```markdown
# Epic K deferred-work delta

Generated: <UTC timestamp> for runId <runId>

## Scope-split (N)

<entries classified as scope-split, in original order>

## Review-finding (M)

<entries classified as review-finding, in original order; entries with
both markers carry the inline note>

## Ambiguous (P)

<entries that matched neither marker set; carry the no-markers note>

## Counts

- Scope-split: N
- Review-finding: M
- Ambiguous: P
- Total new entries: N + M + P
```

## Known limitations

1. **Quick-dev does not emit a structured per-entry format.** Markers
   are inferred from quick-dev's source-language conventions. Classification
   is best-effort. If a future quick-dev grows explicit per-entry
   headers (e.g. `## [scope-split]`), this classifier should be revised
   to use structural matches.
2. **`pre-existing issue` is the single most diagnostic phrase.** Any
   change in quick-dev that drops it would degrade the classifier
   sharply. Worth monitoring upstream.
3. **The `defer` + cascading-context rule uses a ~5-line window.**
   Multi-paragraph entries with the trigger words split by more than
   ~5 lines may not match. The fixture `review-finding-subtle.md`
   exercises the within-window case.

## Verification protocol

To re-verify the classifier against the fixture suite:

1. Read each fixture file under
   `../test-fixtures/deferred-classifier/`
2. Apply the algorithm above
3. Compare against the expected classification table in the fixture
   README
4. Any mismatch is either a bug in this classifier doc or a fixture
   that needs updating

The fixture README documents 2 known knife-edge cases (`both-markers.md`
and `no-markers.md`) where the classifier outcome is correct by rule
but the operator might want different bucketing in practice. Those are
D7 tuning targets in the validation workstream.
