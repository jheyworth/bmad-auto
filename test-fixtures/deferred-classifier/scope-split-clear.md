## Story 3-2 — deferred goals from [S] Split (Step 1 multi-goal check)

During Step 1 clarify-and-route for story `3-2-add-rate-limiter`, the
multi-goal check surfaced three independently shippable goals bundled
into a single spec:

  1. Per-tenant quota enforcement at the inbound edge (the goal the
     spec was actually narrowed to).
  2. Burst-window observability — tenant-tier dashboards that surface
     current consumption vs. ceiling. The spec referenced these in the
     Out-of-scope section but the AC list quietly assumed they would
     ship alongside.
  3. Quota-override admin endpoint — a tenant-scoped manual override
     for support staff. Spec mentioned this in the user-narrative
     section without listing acceptance criteria.

Operator picked `[S] Split` — first goal kept, deferred goals (2) and
(3) appended here. Narrow scope to the first-mentioned goal; spec
rewritten in place per Step 2 §6 "regenerate the spec for the narrowed
scope". Coupling risk: goal (2) reads the same per-tenant counter
goal (1) writes — when goal (2) lands, the counter's read path needs
a tenant-tier join. No data-model changes blocking; the deferred goals
can land in any order after this story.

Deferred goal: tenant-tier burst-window observability dashboards
(originally bundled with 3-2 as "secondary surface"). Spec fragment
preserved below for the future story author:

> "Surface current per-tenant consumption against the burst-window
> ceiling on the tenant admin dashboard. Real-time refresh not
> required; 60s polling is acceptable. Tier-aware (free=60s window,
> paid=10s window)."

Deferred goal: quota-override admin endpoint. Source narrative:

> "Support staff need a tenant-scoped manual override to lift the
> quota for the next N minutes, with an audit-log entry. POST
> /admin/tenants/{id}/quota-override with `{ duration_seconds, reason
> }`."

Recommend follow-up tracking under epic 3 backlog; the observability
goal should land before the admin override since the override needs a
surface to render its effect on.
