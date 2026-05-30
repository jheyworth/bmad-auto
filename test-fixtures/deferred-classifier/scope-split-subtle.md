## Story 4-3 — secondary goals carved off during Step 2 planning

Step 2 plan for `4-3-event-stream-replay` triggered the token-count
split check (Step 2 §6) — the planned implementation exceeded the
single-spec ceiling and was carving across two distinct subsystems.
Rather than press on, proposed the split below and continued to
checkpoint with the narrowed scope.

split: keep the replay-loop core in story 4-3; carve off the
observability hooks and the dead-letter routing into separate stories.

  - main goal (kept): event-stream replay loop reading from
    `events.kafka.replay-backlog`, decoding via the existing
    `EventEnvelope` codec, dispatching through the registered handler
    chain. Bounded retry per event. Spec rewritten in place to cover
    only this scope.
  - secondary goal: observability hooks — emit per-handler latency
    histograms and per-tenant replay-lag gauges to the metrics sink.
    Originally pencilled into AC-5; now deferred.
  - secondary goal: dead-letter routing — events that fail the
    bounded retry should land in `events.kafka.replay-dlq` with
    structured metadata for later inspection. Originally AC-6 plus
    half of AC-7; now deferred.

Coupling notes: the observability hooks read the same handler-chain
result type the main goal produces, so adding them later is purely
additive. Dead-letter routing wraps the main goal's bounded-retry exit
branch — when it lands it will replace the current `log.warn(...)`
with an enqueue call. No interface breaks expected.

Recommendation per Step 2 §6 narrative: tackle the main goal first
(this story), then observability, then dead-letter. Replay-lag gauges
are particularly load-bearing for the upcoming SLO work in epic 5.
