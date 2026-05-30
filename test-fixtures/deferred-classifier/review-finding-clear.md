## Story 2-4 — review findings deferred (Step 4 reviewer pass)

Step 4 review for story `2-4-tenant-onboarding-form` produced three
deferred findings across the blind-hunter and edge-case-hunter
reviewer roles. None of these are caused by the current story's diff;
they are pre-existing issues surfaced incidentally by the review and
collected here for later focused attention.

Defer (blind hunter): `src/forms/validators/email.ts` line 47 — the
email-validator regex has a known false-positive on quoted local-part
addresses (RFC 5321 §4.1.2). The blind hunter flagged it because the
new tenant-onboarding form imports `validateEmail` and inherits the
bug, but the bug pre-dates this story by several quarters (originally
landed in commit `a3f9c12` per `git blame`). Pre-existing issue, not
caused by this change. Track separately under the validation-library
backlog.

Defer (edge case hunter): `src/forms/state/persistence.ts` — the
draft-form persistence layer drops in-flight state when the browser
session expires server-side. The edge case hunter walked the
session-expiry path and observed that the form's
`useDraftPersistence` hook does not detect the expired-session
response and re-renders with stale local data. Tenant-onboarding form
uses this hook (the new code path AC-2 wires up), so the bug is
reachable, but the underlying persistence layer is shared with five
other forms and the fix belongs there. Pre-existing issue, not caused
by this story. Suggest a focused fix story under epic 2's hardening
backlog.

Defer (edge case hunter): the `<TenantTypeSelector>` component
re-renders the entire form tree on tier change because the tier value
is held in the top-level form-state object instead of in a localized
context. This is a known performance smell across the forms package;
the edge case hunter noted it because the tier selector now appears
in the tenant-onboarding flow, but the architectural fix is package-
wide. Not caused by this change. Defer for a forms-package refactor
story.

Review-finding classification per Step 4 §3 cascading order:
intent_gap=0, bad_spec=0, patch=0, defer=3, reject=2 (silenced). No
loopback triggered; story proceeds to Step 5.
