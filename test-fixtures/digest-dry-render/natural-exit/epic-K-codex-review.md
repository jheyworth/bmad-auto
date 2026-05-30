# Codex adversarial review — epic K

- Run: 20260525T120000Z
- Timestamp: 2026-05-25T13:46:02Z
- Diff range: abc1234567890abcdef1234567890abcdef1234..def4567890abcdef1234567890abcdef12345678
- Tracer architecture (Format A): _bmad-output/implementation-artifacts/epic-K-micro-architecture.md
- Invocation: `codex review --base epic-K-auto-dev "<adversarial prompt covering integration drift / cross-story / missed-AC edges>"`

---

## Integration drift from tracer architecture

The tracer architecture established a gateway-level quota enforcement
pattern with tenant-tier-derived burst windows (§ "Burst windows by
tier"). Stories K-2 (rate limiter) and K-4 (tenant onboarding form)
both honor the gateway placement, but K-2's implementation hardcodes
the 60s burst window for free-tier rather than reading from the tier
table. This is the same intent_gap that surfaced and was resolved
mid-loop; the resolution chose option (b) carving out a uniform 60s
override. The architecture document still reads as if tier-derived
windows are the canonical pattern — drift between docs and code.

## Cross-story inconsistency

K-3 (order history pagination) and K-4 (tenant onboarding) each
introduce cursor-based pagination using different cursor encodings.
K-3 uses base64-encoded `{lastId, lastTimestamp}`; K-4 uses opaque
`String` tokens minted server-side. Different shapes for similar
problems; consolidate before more callers grow.

Tenant-tier handling is also split: K-2 reads tier from a hard-coded
table, K-4 reads from the per-tenant settings API. One source of
truth would help.

## Missed acceptance-criterion edges

K-2 AC-3 (burst-window tier handling) is now satisfied for free-tier
only; paid-tier behavior is undefined in the diff. The micro-arch
implies paid=10s but no test exercises that branch.

K-4 AC-5 (session-expiry recovery) is wired but the `useDraftPersistence`
hook does not surface the expired-session response — see the deferred
review-finding for the same code path; the AC's "graceful recovery"
clause is arguably under-implemented even though the deferred fix is
out of scope.

---

End of review. Operator should weigh the tier-handling drift against
the run's overall completeness before merging.
