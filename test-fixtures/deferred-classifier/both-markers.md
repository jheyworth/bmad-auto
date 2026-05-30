## Story 6-1 — deferred goal AND review-finding defers (mixed entry)

Story `6-1-payments-webhook-handler` produced a mixed deferred-work
entry: the operator picked `[S] Split` at Step 1 (so the secondary
goals were appended here), AND the Step 4 review pass surfaced two
pre-existing issues worth deferring. Quick-dev appended both into the
same entry on the same story pass because they share a story id and
landed back-to-back in the run log.

Step 1 split: the payments-webhook spec bundled three things. Operator
picked the inbound-validation core; the deferred goals carved off
follow.

Deferred goal: idempotency-key replay-cache for the webhook receiver.
Originally pencilled into AC-3 ("the same webhook delivered twice MUST
produce one downstream effect"). The narrow-scope rewrite of the spec
removed AC-3 because the proposed implementation (Redis-backed cache
with 24h TTL) is its own story-sized chunk; spec for story 6-1 now
guarantees only at-least-once handling, with idempotency carved off.

Deferred goal: retry-with-backoff loop for downstream failures. The
original spec said the webhook handler should retry the downstream
payment-record write with exponential backoff on transient failures;
this is now a separate concern that will sit on top of the at-least-
once handler.

Step 4 review pass also produced two defers (after split → narrow →
implement → review). The blind hunter and acceptance auditor each
flagged one pre-existing issue not caused by this change:

defer (blind hunter): `src/webhooks/signing.ts` line 88 — the HMAC-
verification helper uses `crypto.timingSafeEqual` only when the input
strings are equal length; the early-return on length mismatch is a
timing oracle. Pre-existing; the webhook receiver in this story
inherits the helper but is not the cause. Not in-scope for story 6-1
because the fix needs a security review of the timing-leak surface
across all callers.

defer (acceptance auditor): the webhook ingress logs the full request
body at INFO level before signature verification. PCI-DSS scope
concern — payment-related payloads may include PAN fragments in
test-mode webhooks. Pre-existing across the webhook framework; not
caused by this change. Compliance backlog.

Marker note for the autonomous-mode classifier: this entry contains
BOTH `deferred goal` / `[S] Split` (scope-split markers) AND
`pre-existing issue` / `not caused by this change` / `blind hunter` /
`acceptance auditor` / `defer` (review-finding markers). Per SKILL.md
stage 7.2.5 the both-markers default is `review-finding` with the
inline note `(both markers matched — defaulted to review-finding)` —
the classifier sees the review-finding markers and prefers them on
the assumption that autonomous-mode directive #2 (`[K] Keep all goals`)
made scope-split rare in dev mode anyway. That default is correct in
spirit for the run-time count, but the entry semantically contains
real deferred goals from Step 1; G3 / D7 may want to revisit whether
mixed entries should be counted in both buckets.
