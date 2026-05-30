## Story 5-2 — Step 4 cascading review classification, defer branch

Reviewer pass for `5-2-search-index-rebuild` ran across the three
roles. Cascading-order processing per Step 4 §3 of quick-dev's
step-04-review.md: intent_gap and bad_spec findings would trigger a
loopback (lower findings moot since code would be re-derived). Neither
fired this iteration. Acceptance auditor produced one patch finding
(auto-applied, see Step 5 summary). The remainder were defer findings,
collected below.

The search-index-rebuild story touches `src/search/indexer/main.ts`,
`src/search/indexer/batch.ts`, and the shared `IndexedField` codec.
The diff conforms to the tracer architecture's batch-rebuild pattern
(epic-5-micro-architecture.md § "Indexer batching"). Three of the
reviewers' observations were classified `defer` rather than `patch`
or `reject` because they are real (not noise → not reject) and
non-trivial to fix in-scope (not a one-line patch).

defer: `src/search/codec/IndexedField.ts` has an off-by-one in the
boundary handling for empty-token arrays — when `tokens.length === 0`,
the byte-offset header is written with `length=1` instead of
`length=0`. Reachable on documents with empty title fields. The
indexer code in this story does not produce such documents (AC-2
guards against them), but the codec defect is real. Not a patch
because the fix needs a codec-version bump and the on-disk index needs
a migration — neither belongs to story 5-2.

defer: the batched index-write path in `batch.ts` opens a new file
descriptor per batch instead of reusing a pooled writer. The edge-case
hunter measured a 14ms per-batch fixed cost on the local benchmark
(batch size 1000). At the current ingest volume (~50 batches/minute)
this is invisible; at the scale epic 5's PRD targets (~5000
batches/minute) it would dominate. The hunter explicitly flagged this
with "intent_gap?" but the spec is clear that throughput is not an AC
for this story — the architecture document is silent on writer
pooling. So: defer, not bad_spec, not intent_gap. Track under the
performance backlog for epic 5.

defer: the `IndexedField.encode` function has an undocumented dependency
on the host system's `LANG` environment variable (it uses
`String.prototype.localeCompare` without an explicit locale). Reject
was considered (no behavior change at the current `LANG=en_US.UTF-8`
default) but the acceptance auditor argued correctly that this is the
exact class of pre-existing issue defer is for: a real correctness
trap, not caused by this story's diff, but worth tracking. The patch
would be small but it needs a separate decision about which locale to
pin to.

No loopback. patch=1 (auto-applied), defer=3 (this entry), reject=2.
Story 5-2 proceeds to Step 5.
