# Epic 7 — Spike triage log

> **Epic:** Add SSO via Okta (Org-level federated identity for the
> admin console; SCIM provisioning is out of scope for this epic.)
> **Run:** first `/bmad-auto --prep --epics 7` invocation
> **Triage pass:** initial (Stage 1.f, all items defer)

- 2026-05-25T09:14:02Z [DEFER] K-spike-01 — [ASSUMPTION] (brief.md): "Okta is the only IdP we need to support in v1; multi-IdP support can ship later." — Source: brief.md line 47 — Reason: tracer (K-1) only exercises one IdP code path; multi-IdP routing surfaces in epic 8, not here. Dev-safe.
- 2026-05-25T09:14:38Z [DEFER] K-spike-02 — open_question (SPEC.md, touching CAP-3): "Should the Okta session cookie be readable by sub-domains, or scoped to the admin-console host only?" — Source: SPEC.md `open_questions[]` — Reason: admin console is the only sub-domain in scope this epic; host-only scoping is the dev-safe default and matches existing internal-tools cookie policy. Revisit if customer portal joins SSO in a later epic.
- 2026-05-25T09:15:11Z [DEFER] K-spike-03 — gap (epics.md Step-4): "Stories 7-2 and 7-3 reference 'org-mapping' but no AC defines whether org mapping is derived from Okta groups or from a separate config table." — Source: epics.md epic-7 Step-4 validation gaps — Reason: tracer story (7-1) uses a hardcoded single-org mapping by design; the org-mapping mechanism is a 7-2 implementation choice that the dev agent will surface as a sub-decision. Not a tracer blocker.
- 2026-05-25T09:15:44Z [DEFER] K-spike-04 — architecture gap (Important): "JWT validation library not yet selected — architecture.md Section 7 lists 'jose vs jsonwebtoken vs panva/jose' as undecided." — Source: architecture.md Section 7 Gap Analysis — Reason: dev agent will pick during 7-1 implementation per project conventions (panva/jose is already a transitive dep). Logged as decision-to-make, not blocker.

_End of initial triage. 4 items, all DEFER, 0 BLOCK, 0 SPIKE. Phase 1.f proceeds to Stage 1.g (tracer-bullet readiness)._
