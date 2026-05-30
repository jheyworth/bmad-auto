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
  - 'docs/test-design-E5.md'
---

# NFR Evidence Audit - Streaming CSV export

**Date:** 2026-05-26
**Story:** E5 (epic-level audit)
**Overall Status:** CONCERNS ⚠️

---

Note: This audit summarizes existing implementation evidence; it does not run tests or CI workflows. NFR thresholds and planned evidence should come from PRD, architecture, and `test-design` outputs where available.

## Executive Summary

**Assessment:** 9 PASS, 6 CONCERNS, 0 FAIL

**Blockers:** 0 release blockers — but two CONCERNS-class items materially raise operational risk.

**High Priority Issues:** 2 high-priority issues outstanding (back-pressure under sustained 50MB-export load; missing end-to-end memory-ceiling test for the streaming path)

**Recommendation:** Hold release until the two high-priority CONCERNS are addressed. The remaining four CONCERNS are tracked as short-term follow-ups.

---

## Performance Assessment

### Response Time (p95)

- **Status:** CONCERNS ⚠️
- **Threshold:** ≤2.5s p95 time-to-first-byte for exports up to 50MB
- **Actual:** 2.1s p95 TTFB at 25MB; degrades to 3.4s p95 at 50MB
- **Evidence:** k6 export benchmark — `_bmad-output/E5/perf/k6-export-2026-05-22.json`
- **Findings:** The 50MB upper bound exceeds the published TTFB SLO. Profiling shows the regression is in the global-sort step (AC-4), not the streaming path itself.

### Throughput

- **Status:** PASS ✅
- **Threshold:** ≥10 concurrent exports per pod, no queue starvation
- **Actual:** 12 concurrent exports sustained for 20 minutes; no queue depth growth
- **Evidence:** k6 export benchmark — `_bmad-output/E5/perf/k6-export-2026-05-22.json`
- **Findings:** Throughput holds; the bottleneck is per-export latency, not concurrency.

### Resource Usage

- **CPU Usage**
  - **Status:** PASS ✅
  - **Threshold:** ≤70% steady-state CPU at 10 concurrent exports
  - **Actual:** 58% steady-state CPU
  - **Evidence:** CloudWatch — `_bmad-output/E5/perf/cw-2026-05-22.png`

- **Memory Usage**
  - **Status:** CONCERNS ⚠️
  - **Threshold:** ≤50MB RSS per in-flight export (AC-1 streaming guarantee)
  - **Actual:** 42MB RSS p95 per export; spikes to 110MB during the global-sort phase
  - **Evidence:** Prometheus scrape — `_bmad-output/E5/perf/prom-rss.csv`
  - **Findings:** The streaming guarantee is observed across the streaming path but violated during the sort phase. This contradicts AC-1's assertion that no export ever holds the full result set in memory.

### Scalability

- **Status:** PASS ✅
- **Threshold:** Linear horizontal scale to 4 pods
- **Actual:** 3.7x throughput at 4 pods vs single-pod baseline
- **Evidence:** Multi-pod load profile — `_bmad-output/E5/perf/multipod-2026-05-23.json`
- **Findings:** No shared-state contention; export jobs are stateless and Redis-coordinated only for tenant quota.

---

## Security Assessment

### Authentication Strength

- **Status:** PASS ✅
- **Threshold:** OAuth2 client-credentials with rotated secrets
- **Actual:** OAuth2 client-credentials enforced; secret rotation at 22 days mean age
- **Evidence:** Vault audit log — `_bmad-output/E5/sec/vault-audit-2026-05-25.json`
- **Findings:** No long-lived secrets in scope.

### Authorization Controls

- **Status:** PASS ✅
- **Threshold:** Per-tenant export isolation; no cross-tenant data leakage in any export
- **Actual:** Tenant-id scoping enforced at the query-builder layer; 18 cross-tenant probe tests all return 403
- **Evidence:** Authz test report — `_bmad-output/E5/sec/authz-probe-2026-05-24.md`
- **Findings:** No cross-tenant leakage observed.

### Data Protection

- **Status:** PASS ✅
- **Threshold:** TLS 1.3 in transit; presigned URLs ≤15 minute TTL for download
- **Actual:** TLS 1.3 confirmed; presigned URLs issued with 10-minute TTL
- **Evidence:** SSL Labs report — `_bmad-output/E5/sec/ssllabs-2026-05-25.html`
- **Findings:** Download surface is appropriately ephemeral.

### Vulnerability Management

- **Status:** PASS ✅
- **Threshold:** 0 critical, ≤2 high CVEs in production-path dependencies
- **Actual:** 0 critical, 0 high
- **Evidence:** Snyk scan — `_bmad-output/E5/sec/snyk-2026-05-25.json`
- **Findings:** Clean scan.

### Compliance (if applicable)

- **Status:** CONCERNS ⚠️
- **Standards:** GDPR data-subject export requirements
- **Actual:** Export contents conform; audit-log retention for export operations is 30 days vs required 90 days
- **Evidence:** Compliance audit — `_bmad-output/E5/sec/compliance-2026-05-25.md`
- **Findings:** The 30→90 day audit-log retention gap is the highest-priority CONCERNS item. Not a release blocker if GDPR scope is internally scoped to non-PII exports, but flagged for compliance review.

---

## Reliability Assessment

### Availability (Uptime)

- **Status:** PASS ✅
- **Threshold:** 99.9% over a 30-day rolling window
- **Actual:** 99.94% over the last 30 days
- **Evidence:** Datadog uptime monitor — `_bmad-output/E5/rel/datadog-uptime-2026-05-26.csv`
- **Findings:** Within SLO.

### Error Rate

- **Status:** CONCERNS ⚠️
- **Threshold:** <0.5% export-failure rate
- **Actual:** 0.7% export-failure rate, predominantly on exports >40MB
- **Evidence:** Application logs — `_bmad-output/E5/rel/export-failures-2026-05.log`
- **Findings:** Failure rate exceeds threshold for the upper export-size band. Root-caused to the same memory-ceiling violation surfaced in the Performance section.

### MTTR (Mean Time To Recovery)

- **Status:** PASS ✅
- **Threshold:** ≤30 minutes for SEV-2 export-service incidents
- **Actual:** No SEV-2 incidents in the audit window
- **Evidence:** Incident timeline — `_bmad-output/E5/rel/incidents-2026-Q1.csv`
- **Findings:** No production incidents originating from the export service.

### Fault Tolerance

- **Status:** CONCERNS ⚠️
- **Threshold:** Resumable exports after pod restart
- **Actual:** Resumability is partially implemented — checkpoint state is written but not consumed on restart
- **Evidence:** Manual probe — `_bmad-output/E5/rel/resumability-probe-2026-05-24.md`
- **Findings:** A pod restart mid-export causes the export to fail rather than resume. Affects long-running exports; tracked for E5.S6 (deferred from this epic).

### CI Burn-In (Stability)

- **Status:** PASS ✅
- **Threshold:** ≥75 consecutive successful integration-suite runs
- **Actual:** 92 consecutive successful runs
- **Evidence:** CI burn-in report — `_bmad-output/E5/rel/ci-burnin-2026-05-26.log`
- **Findings:** Test suite is stable.

### Disaster Recovery (if applicable)

- **RTO (Recovery Time Objective)**
  - **Status:** PASS ✅
  - **Threshold:** ≤30 minutes
  - **Actual:** 22 minutes in the most recent DR drill
  - **Evidence:** DR drill report — `_bmad-output/E5/rel/dr-drill-2026-04-12.md`

- **RPO (Recovery Point Objective)**
  - **Status:** PASS ✅
  - **Threshold:** ≤5 minutes
  - **Actual:** 2 minutes
  - **Evidence:** DR drill report — `_bmad-output/E5/rel/dr-drill-2026-04-12.md`

---

## Maintainability Assessment

### Test Coverage

- **Status:** CONCERNS ⚠️
- **Threshold:** ≥80% line coverage on production paths
- **Actual:** 76% line coverage, 71% branch coverage
- **Evidence:** Coverage report — `_bmad-output/E5/maint/coverage-2026-05-26.html`
- **Findings:** Below threshold. Uncovered code concentrated in the global-sort branch (the same code path implicated in memory and error-rate findings).

### Code Quality

- **Status:** PASS ✅
- **Threshold:** SonarQube maintainability rating ≥B
- **Actual:** Maintainability rating A
- **Evidence:** SonarQube report — `_bmad-output/E5/maint/sonar-2026-05-26.pdf`
- **Findings:** Code quality holds.

### Technical Debt

- **Status:** PASS ✅
- **Threshold:** <8% debt ratio
- **Actual:** 4.6% debt ratio
- **Evidence:** SonarQube report — `_bmad-output/E5/maint/sonar-2026-05-26.pdf`
- **Findings:** Within budget.

### Documentation Completeness

- **Status:** CONCERNS ⚠️
- **Threshold:** ≥85% of public API documented
- **Actual:** 72% of public API documented
- **Evidence:** Doc audit — `_bmad-output/E5/maint/doc-audit-2026-05-26.md`
- **Findings:** The export-service public API surface added two new endpoints in this epic, neither documented yet.
- **Recommendation:** Document the two new endpoints (`/export/csv/stream`, `/export/csv/status`) before release.

### Test Quality (from test-review, if available)

- **Status:** PASS ✅
- **Threshold:** Test review report shows no critical findings
- **Actual:** Test review 2026-05-23 surfaced 0 critical, 2 medium, 5 low findings
- **Evidence:** Test review report — `_bmad-output/E5/maint/test-review-2026-05-23.md`
- **Findings:** Medium findings tracked; none block release.

---

## Quick Wins

3 quick wins identified for immediate implementation:

1. **Document new export endpoints** (Maintainability) - HIGH - 3 hours
   - Add OpenAPI specs and runbook entries for `/export/csv/stream` and `/export/csv/status`.

2. **Extend export-log retention from 30 to 90 days** (Security/Compliance) - HIGH - 1 hour
   - Config change in the logging pipeline; no code changes.

3. **Add an end-to-end memory-ceiling test for the streaming export path** (Performance) - HIGH - 4 hours
   - Closes the AC-1 verification gap and gates the memory regression.

---

## Recommended Actions

### Immediate (Before Release) - CRITICAL/HIGH Priority

1. **Resolve the global-sort memory spike on >40MB exports** - HIGH - 1-2 days - Platform team
   - Replace the in-memory sort with a disk-spilling sort for the >40MB band, OR document the size cap and reject larger exports with 413.
   - Validation: memory-ceiling e2e test passes for the 50MB upper bound.

2. **Extend export audit-log retention from 30 to 90 days** - HIGH - 1 hour - SRE team
   - Closes the GDPR retention gap.

3. **Document the two new public API endpoints** - HIGH - 3 hours - Platform team
   - Brings doc completeness back above the 85% threshold.

### Short-term (Next Milestone) - MEDIUM Priority

1. **Restore resumability after pod restart** - MEDIUM - 1 week - Platform team
   - Deferred from E5.S6; track for Epic 6.

2. **Lift line coverage on the export path to ≥80%** - MEDIUM - 2 days - Platform team
   - Most uncovered code is in the global-sort branch; coupled with #1 above.

### Long-term (Backlog) - LOW Priority

1. **Evaluate replacing the CSV export with a Parquet/columnar option** - LOW - 2 weeks - Platform team
   - Future product question; not in scope.

---

## Monitoring Hooks

3 monitoring hooks recommended to detect issues before failures:

### Performance Monitoring

- [ ] Per-export memory-usage histogram — alert when any single export exceeds 80MB RSS
  - **Owner:** SRE team
  - **Deadline:** 2026-06-02

### Reliability Monitoring

- [ ] Export-failure rate dashboard — alert at 0.5% over a 10-minute rolling window
  - **Owner:** SRE team
  - **Deadline:** 2026-06-02

### Alerting Thresholds

- [ ] Export-job runtime anomaly detection — alert when p95 runtime exceeds 4s
  - **Owner:** SRE team
  - **Deadline:** 2026-06-02

---

## Fail-Fast Mechanisms

2 fail-fast mechanisms recommended to prevent failures:

### Rate Limiting (Performance)

- [ ] Per-tenant export concurrency cap (max 3 concurrent exports per tenant)
  - **Owner:** Platform team
  - **Estimated Effort:** 4 hours

### Validation Gates (Security)

- [ ] Export-size cap at 50MB enforced at ingress with explicit 413 response
  - **Owner:** Platform team
  - **Estimated Effort:** 2 hours (couples with the global-sort resolution above)

---

## Evidence Gaps

2 evidence gaps identified - action required:

- [ ] **End-to-end memory-ceiling test for streaming path** (Performance)
  - **Owner:** Platform team
  - **Deadline:** 2026-06-02
  - **Suggested Evidence:** Playwright test driving a 50MB export with memory assertion via heap snapshot
  - **Impact:** Without this test, the AC-1 streaming guarantee is not verifiable in CI.

- [ ] **Resumability soak test** (Reliability)
  - **Owner:** Platform team
  - **Deadline:** 2026-06-09
  - **Suggested Evidence:** Chaos-engineering kill-pod-mid-export run with export-completion assertion
  - **Impact:** Without this evidence, the fault-tolerance CONCERNS cannot be downgraded.

---

## Findings Summary

**Based on ADR Quality Readiness Checklist (8 categories, 29 criteria)**

| Category                                         | Criteria Met       | PASS             | CONCERNS             | FAIL             | Overall Status                      |
| ------------------------------------------------ | ------------------ | ---------------- | -------------------- | ---------------- | ----------------------------------- |
| 1. Testability & Automation                      | 3/4                | 3                | 1                    | 0                | CONCERNS ⚠️                          |
| 2. Test Data Strategy                            | 3/3                | 3                | 0                    | 0                | PASS ✅                              |
| 3. Scalability & Availability                    | 3/4                | 3                | 1                    | 0                | CONCERNS ⚠️                          |
| 4. Disaster Recovery                             | 3/3                | 3                | 0                    | 0                | PASS ✅                              |
| 5. Security                                      | 3/4                | 3                | 1                    | 0                | CONCERNS ⚠️                          |
| 6. Monitorability, Debuggability & Manageability | 3/4                | 3                | 1                    | 0                | CONCERNS ⚠️                          |
| 7. QoS & QoE                                     | 2/4                | 2                | 2                    | 0                | CONCERNS ⚠️                          |
| 8. Deployability                                 | 2/3                | 2                | 1                    | 0                | CONCERNS ⚠️                          |
| **Total**                                        | **22/29**          | **22**           | **7**                | **0**            | **CONCERNS ⚠️**                      |

**Criteria Met Scoring:**

- ≥26/29 (90%+) = Strong foundation
- 20-25/29 (69-86%) = Room for improvement
- <20/29 (<69%) = Significant gaps

---

## Gate YAML Snippet

```yaml
nfr_assessment:
  date: '2026-05-26'
  story_id: 'E5'
  feature_name: 'Streaming CSV export'
  adr_checklist_score: '22/29' # ADR Quality Readiness Checklist
  categories:
    testability_automation: 'CONCERNS'
    test_data_strategy: 'PASS'
    scalability_availability: 'CONCERNS'
    disaster_recovery: 'PASS'
    security: 'CONCERNS'
    monitorability: 'CONCERNS'
    qos_qoe: 'CONCERNS'
    deployability: 'CONCERNS'
  overall_status: 'CONCERNS'
  critical_issues: 0
  high_priority_issues: 3
  medium_priority_issues: 4
  concerns: 7
  blockers: false
  quick_wins: 3
  evidence_gaps: 2
  recommendations:
    - 'Resolve global-sort memory spike on >40MB exports (HIGH, 1-2d).'
    - 'Extend export audit-log retention from 30 to 90 days for GDPR (HIGH, 1h).'
    - 'Document the two new public API endpoints before release (HIGH, 3h).'
```

---

## Related Artifacts

- **Story File:** _bmad-output/stories/E5/ (epic-level audit)
- **Tech Spec:** docs/architecture.md#export-service
- **PRD:** docs/prd.md#streaming-csv-export
- **Test Design:** docs/test-design-E5.md
- **Evidence Sources:**
  - Test Results: _bmad-output/E5/perf/
  - Metrics: _bmad-output/E5/perf/, _bmad-output/E5/rel/
  - Logs: _bmad-output/E5/rel/
  - CI Results: _bmad-output/E5/rel/ci-burnin-2026-05-26.log

---

## Recommendations Summary

**Release Blocker:** No hard blockers, but three HIGH-priority items materially raise operational risk if released as-is.

**High Priority:** Global-sort memory spike resolution; export audit-log retention extension; new-endpoint documentation.

**Medium Priority:** Restore resumability; lift line coverage above 80%.

**Next Steps:** Address the three HIGH-priority items and re-run `*nfr-assess`. If CONCERNS holds after fixes, proceed to gate with operator sign-off on the residual MEDIUM-priority items.

---

## Sign-Off

**NFR Evidence Audit:**

- Overall Status: CONCERNS ⚠️
- Critical Issues: 0
- High Priority Issues: 3
- Concerns: 7
- Evidence Gaps: 2

**Gate Status:** CONCERNS ⚠️

**Next Actions:**

- If PASS ✅: Proceed to `*gate` workflow or release
- If CONCERNS ⚠️: Address HIGH/CRITICAL issues, re-run `*nfr-assess`
- If FAIL ❌: Resolve FAIL status NFRs, re-run `*nfr-assess`

**Generated:** 2026-05-26
**Workflow:** testarch-nfr v5.0

---

<!-- Powered by BMAD-CORE™ -->
