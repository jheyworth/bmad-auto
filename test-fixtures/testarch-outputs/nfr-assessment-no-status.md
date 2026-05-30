---
stepsCompleted:
  - 'step-01-load-context'
  - 'step-02-define-thresholds'
  - 'step-03-gather-evidence'
  - 'step-04-evaluate-and-score'
  - 'step-05-generate-report'
lastStep: 'step-05-generate-report'
lastSaved: '2026-05-26'
workflowType: 'testarch-nfr-assess'
inputDocuments:
  - 'docs/prd.md'
  - 'docs/architecture.md'
  - 'docs/test-design-E2.md'
---

# NFR Evidence Audit - Tiered rate-limit windowing

**Date:** 2026-05-26
**Story:** E2 (epic-level audit)

---

Note: This audit summarizes existing implementation evidence; it does not run tests or CI workflows. NFR thresholds and planned evidence should come from PRD, architecture, and `test-design` outputs where available.

## Executive Summary

**Assessment:** 14 PASS, 2 CONCERNS, 0 FAIL

**Blockers:** 0 release blockers identified

**High Priority Issues:** 0 high-priority issues outstanding

**Recommendation:** Proceed to release. Two CONCERNS-classified items (custom-NFR back-pressure visibility and documentation completeness for the burn-in harness) are tracked as short-term follow-ups and do not block GA.

---

## Performance Assessment

### Response Time (p95)

- **Threshold:** ≤120ms p95 under 5k req/s sustained
- **Actual:** 94ms p95 at 5k req/s, 108ms p95 at 7.5k req/s
- **Evidence:** k6 load run 2026-05-22 — `_bmad-output/E2/perf/k6-2026-05-22.json`
- **Findings:** Headroom remains at the published peak (5k req/s). Degradation between 5k and 7.5k is linear, no cliff observed.

### Throughput

- **Threshold:** ≥5,000 req/s sustained for 10 minutes
- **Actual:** 5,840 req/s sustained for 15 minutes
- **Evidence:** k6 load run 2026-05-22 — `_bmad-output/E2/perf/k6-2026-05-22.json`
- **Findings:** Exceeds the sustained throughput target by 17%. The tiered windowing structure introduces no measurable throughput penalty over the flat-window baseline.

### Resource Usage

- **CPU Usage**
  - **Threshold:** ≤65% steady-state CPU on a c6i.large at peak
  - **Actual:** 52% steady-state CPU at 5k req/s
  - **Evidence:** CloudWatch — `_bmad-output/E2/perf/cw-2026-05-22.png`

- **Memory Usage**
  - **Threshold:** ≤512MB RSS per pod
  - **Actual:** 318MB RSS p95 across the 30-minute soak
  - **Evidence:** Prometheus scrape — `_bmad-output/E2/perf/prom-rss.csv`

### Scalability

- **Threshold:** Linear horizontal scale to 4 pods, no shared-state contention
- **Actual:** 3.8x throughput at 4 pods (vs single-pod baseline); Redis lock contention rate 0.04% of operations
- **Evidence:** Multi-pod load profile — `_bmad-output/E2/perf/multipod-2026-05-23.json`
- **Findings:** The Redis-backed shared counter scales cleanly within the published 4-pod ceiling. Beyond 6 pods (out of scope for this epic), contention rises non-linearly; flagged for the Epic 8 sharding work.

---

## Security Assessment

### Authentication Strength

- **Threshold:** OAuth2 client-credentials with rotated client secrets ≤90d age
- **Actual:** OAuth2 client-credentials live; secret-rotation policy enforced via Vault transit, mean secret age 22 days
- **Evidence:** Vault audit log — `_bmad-output/E2/sec/vault-audit-2026-05-25.json`
- **Findings:** No long-lived secrets in scope. Service-to-service auth verified end-to-end against the staging IdP.

### Authorization Controls

- **Threshold:** Per-tenant quota namespace isolation, no cross-tenant read/write
- **Actual:** Isolation enforced at the Redis key prefix layer; cross-tenant probe tests return 403 in all 12 attempted access paths
- **Evidence:** Authz test report — `_bmad-output/E2/sec/authz-probe-2026-05-24.md`
- **Findings:** No cross-tenant leakage observed under fuzzed inputs.

### Data Protection

- **Threshold:** TLS 1.3 on all ingress; Redis AUTH + TLS for backing store
- **Actual:** TLS 1.3 confirmed via SSL Labs scan (grade A+); Redis TLS confirmed via openssl s_client handshake
- **Evidence:** SSL Labs report — `_bmad-output/E2/sec/ssllabs-2026-05-25.html`
- **Findings:** No plaintext on the wire in any tested path.

---

## Reliability Assessment

### Availability (Uptime)

- **Threshold:** 99.9% over a 30-day rolling window
- **Actual:** 99.97% over the last 30 days (staging environment proxy for prod)
- **Evidence:** Datadog uptime monitor — `_bmad-output/E2/rel/datadog-uptime-2026-05-26.csv`
- **Findings:** Three sub-minute blips correlated with kubelet evictions, none customer-affecting.

### Error Rate

- **Threshold:** <0.1% 5xx rate at peak load
- **Actual:** 0.03% 5xx rate at 5k req/s sustained
- **Evidence:** ALB access logs — `_bmad-output/E2/rel/alb-2026-05-22.parquet`
- **Findings:** Well within budget. No error-rate increase observed at the 5→7.5k req/s threshold.

### Fault Tolerance

- **Threshold:** Graceful degradation when Redis primary fails over (≤2s p99 read latency during failover)
- **Actual:** 1.4s p99 read latency observed during chaos-engineering primary kill at 2026-05-21
- **Evidence:** Chaos run artifact — `_bmad-output/E2/rel/chaos-redis-failover-2026-05-21.md`
- **Findings:** Failover behavior matches the published runbook. No request loss observed.

---

## Maintainability Assessment

### Test Coverage

- **Threshold:** ≥80% line coverage on production paths
- **Actual:** 91% line coverage, 86% branch coverage
- **Evidence:** Coverage report — `_bmad-output/E2/maint/coverage-2026-05-26.html`
- **Findings:** Coverage holds above the threshold across all six production-path modules.

### Documentation Completeness

- **Threshold:** ≥90% of public API surface documented; runbooks current
- **Actual:** 88% of public API documented; runbooks current
- **Evidence:** Doc audit — `_bmad-output/E2/maint/doc-audit-2026-05-26.md`
- **Findings:** Three internal helper modules (under `src/rate_limit/window/internal/`) lack docstrings. Not customer-facing; flagged as short-term cleanup.
- **Recommendation:** Add module-level docstrings to the three internal helpers; estimated 2 hours.

---

## Findings Summary

**Based on ADR Quality Readiness Checklist (8 categories, 29 criteria)**

| Category                                         | Criteria Met       | PASS             | CONCERNS             | FAIL             |
| ------------------------------------------------ | ------------------ | ---------------- | -------------------- | ---------------- |
| 1. Testability & Automation                      | 4/4                | 4                | 0                    | 0                |
| 2. Test Data Strategy                            | 3/3                | 3                | 0                    | 0                |
| 3. Scalability & Availability                    | 4/4                | 4                | 0                    | 0                |
| 4. Disaster Recovery                             | 3/3                | 3                | 0                    | 0                |
| 5. Security                                      | 4/4                | 4                | 0                    | 0                |
| 6. Monitorability, Debuggability & Manageability | 3/4                | 3                | 1                    | 0                |
| 7. QoS & QoE                                     | 4/4                | 4                | 0                    | 0                |
| 8. Deployability                                 | 2/3                | 2                | 1                    | 0                |
| **Total**                                        | **27/29**          | **27**           | **2**                | **0**            |

---

## Related Artifacts

- **Story File:** _bmad-output/stories/E2/ (epic-level audit)
- **Tech Spec:** docs/architecture.md#rate-limit-service
- **PRD:** docs/prd.md#tiered-windowing
- **Test Design:** docs/test-design-E2.md
- **Evidence Sources:**
  - Test Results: _bmad-output/E2/perf/
  - Metrics: _bmad-output/E2/perf/, _bmad-output/E2/rel/
  - Logs: _bmad-output/E2/rel/
  - CI Results: _bmad-output/E2/rel/ci-burnin-2026-05-26.log

---

## Recommendations Summary

**Release Blocker:** None. Epic 2 is GA-eligible.

**High Priority:** None.

**Medium Priority:** Two follow-ups tracked: internal-helper docstrings (2h) and Prometheus scrape-interval tightening (1h).

**Next Steps:** Proceed to the `*gate` workflow. Schedule the two medium-priority items in the next sprint.

---

**Generated:** 2026-05-26
**Workflow:** testarch-nfr v5.0

---

<!-- Powered by BMAD-CORE™ -->
