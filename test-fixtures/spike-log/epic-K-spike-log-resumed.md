# Epic 7 — Spike triage log

> **Epic:** Add SSO via Okta (Org-level federated identity for the
> admin console; SCIM provisioning is out of scope for this epic.)
> **Run:** second `/bmad-auto --epics 7` invocation (resumed after
> operator resolved K-spike-04 between runs)
> **Triage pass:** resumed (Stage 1.f, skip-already-resolved protocol applied)

## Carried over from prior run (2026-05-25T09:14–09:16)

Stage 1.f read this log on entry. Items already classified as `defer`
or `spike` (resolved) are preserved verbatim; no re-prompting.

- 2026-05-25T09:14:02Z [DEFER] K-spike-01 — [ASSUMPTION] (brief.md): "Okta is the only IdP we need to support in v1; multi-IdP support can ship later." — Source: brief.md line 47 — Reason: tracer (K-1) only exercises one IdP code path; multi-IdP routing surfaces in epic 8, not here. Dev-safe. **[carried over — prior decision preserved]**
- 2026-05-25T09:14:38Z [DEFER] K-spike-02 — open_question (SPEC.md, touching CAP-3): "Should the Okta session cookie be readable by sub-domains, or scoped to the admin-console host only?" — Source: SPEC.md `open_questions[]` — Reason: admin console is the only sub-domain in scope this epic; host-only scoping is the dev-safe default and matches existing internal-tools cookie policy. **[carried over — prior decision preserved]**
- 2026-05-25T09:15:11Z [SPIKE] K-spike-03 — gap (epics.md Step-4): "Stories 7-2 and 7-3 reference 'org-mapping' but no AC defines whether org mapping is derived from Okta groups or from a separate config table." — Source: epics.md epic-7 Step-4 validation gaps — Action: ran `bmad-technical-research` inline; recommend `groups`-claim primary with config-table override. Decision recorded; story 7-2 AC updated. Resolved. **[carried over — spike resolution preserved]**
- 2026-05-25T09:16:19Z [DEFER] K-spike-05 — domain unknown (SPIKES 1e Q3): "Login-latency NFR threshold — is `<800ms p95` from the platform NFR doc the right bar for SSO redirect-loop round-trip, or do we want a tighter SSO-specific bar?" — Source: Stage 1.e SPIKES checklist Q3 (domain unknowns) — Reason: platform-wide `<800ms p95` is the dev-safe default. Phase 4.b NFR audit will measure actual; we re-evaluate then. **[carried over — prior decision preserved]**

## Resolved on this run (previously BLOCK, now cleared)

- 2026-05-25T09:15:44Z [BLOCK] K-spike-04 — architecture gap (Critical): "Production Okta tenant URL + IdP metadata XML have not been provisioned by IT. Tracer story 7-1 cannot authenticate end-to-end without these." — Source: architecture.md Section 7 Gap Analysis — Originally HALTed Stage 1.f.
- 2026-05-25T11:42:08Z [RESOLVED] K-spike-04 — Resolved by: justin.heyworth (operator) — IT ticket OPS-4471 closed 2026-05-25T11:30Z; dev-tenant URL `https://forge-dev.okta.com` provisioned with metadata XML at `secrets/okta-dev-metadata.xml` (gitignored). Architecture gap closed; tracer 7-1 can proceed. **[block cleared on this run; no remaining unresolved block items]**

## New items extracted on this run

_(No new unknowns surfaced; Stages 1.d and 1.e re-walked clean against
the now-resolved spec/architecture state. If new items had surfaced,
they would be appended below this header.)_

---

_End of resumed triage. 5 carried-over items + 1 resolution entry. 3 DEFER (preserved), 1 SPIKE (preserved, previously resolved), 1 BLOCK → RESOLVED. No unresolved BLOCK items remain — Stage 1.f passes; flow proceeds to Stage 1.g (tracer-bullet readiness)._
