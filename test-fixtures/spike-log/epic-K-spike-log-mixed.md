# Epic 7 — Spike triage log

> **Epic:** Add SSO via Okta (Org-level federated identity for the
> admin console; SCIM provisioning is out of scope for this epic.)
> **Run:** first `/bmad-auto --prep --epics 7` invocation
> **Triage pass:** realistic mix (Stage 1.f, defer + block + spike)

- 2026-05-25T09:14:02Z [DEFER] K-spike-01 — [ASSUMPTION] (brief.md): "Okta is the only IdP we need to support in v1; multi-IdP support can ship later." — Source: brief.md line 47 — Reason: tracer (K-1) only exercises one IdP code path; multi-IdP routing surfaces in epic 8, not here. Dev-safe.
- 2026-05-25T09:14:38Z [DEFER] K-spike-02 — open_question (SPEC.md, touching CAP-3): "Should the Okta session cookie be readable by sub-domains, or scoped to the admin-console host only?" — Source: SPEC.md `open_questions[]` — Reason: admin console is the only sub-domain in scope this epic; host-only scoping is the dev-safe default and matches existing internal-tools cookie policy.
- 2026-05-25T09:15:11Z [SPIKE] K-spike-03 — gap (epics.md Step-4): "Stories 7-2 and 7-3 reference 'org-mapping' but no AC defines whether org mapping is derived from Okta groups or from a separate config table." — Source: epics.md epic-7 Step-4 validation gaps — Action: ran `bmad-technical-research` inline against "Okta groups claim vs separate org-mapping table for multi-tenant SaaS" — Result (logged to `_bmad-output/.run-state/epic-7-spike-K-spike-03-result.md`): Okta `groups` claim is reliable when configured via Profile Editor; recommend `groups`-claim primary with config-table override for edge cases (org rename, group rename). Decision recorded; story 7-2 AC updated to reference the recommendation. Resolved.
- 2026-05-25T09:15:44Z [BLOCK] K-spike-04 — architecture gap (Critical): "Production Okta tenant URL + IdP metadata XML have not been provisioned by IT. Tracer story 7-1 cannot authenticate end-to-end without these." — Source: architecture.md Section 7 Gap Analysis — Cannot proceed. Tracer (7-1) requires a real Okta tenant + metadata to exercise the SSO flow concretely; mocking defeats the tracer's purpose (validates real integration). Pending: IT ticket OPS-4471 to provision the dev-tenant.
- 2026-05-25T09:16:19Z [DEFER] K-spike-05 — domain unknown (SPIKES 1e Q3): "Login-latency NFR threshold — is `<800ms p95` from the platform NFR doc the right bar for SSO redirect-loop round-trip, or do we want a tighter SSO-specific bar?" — Source: Stage 1.e SPIKES checklist Q3 (domain unknowns) — Reason: platform-wide `<800ms p95` is the dev-safe default; tighter bar would require benchmarking we haven't done. Phase 4.b NFR audit will measure actual; we re-evaluate then.

_End of mixed triage. 5 items: 3 DEFER, 1 SPIKE (resolved inline), 1 BLOCK (unresolved). Stage 1.f HALTs per SKILL.md:_

> Blocked unknowns prevent Phase 2 entry:
> 1. K-spike-04 — Production Okta tenant URL + IdP metadata XML have not been provisioned by IT. Tracer story 7-1 cannot authenticate end-to-end without these.
>
> Resolve manually (run spike skills) then re-invoke
> `/bmad-auto --epics 7`. The spike-log persists your prior triage.
