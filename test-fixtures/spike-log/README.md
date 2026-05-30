# Spike-log fixtures — Phase 1.f persistence + resume

Fixtures exercising the per-epic spike-triage log format and the
resumable-run protocol that v4 introduces in [SKILL.md Stage 1.f](../../../../skills/bmad-auto/SKILL.md).

## Why these fixtures exist

The spike-log is the load-bearing v4 contribution for Phase 1
hardening: it persists Stage 1.f triage decisions to
`_bmad-output/.run-state/epic-K-spike-log.md` so that when
`/bmad-auto` re-runs against the same epic (after compaction, after
operator HALT-and-resolve, after a session crash) Stage 1.f reads the
log on entry, skips already-resolved items, and HALTs only if an
unresolved `block` remains.

These three snapshots + this README give:

- **G1 reviewers** a concrete shape for the spike-log format and a
  worked example of the resume protocol they can sign off on
- **G2v4 (operator-run Phase 1 gate)** a reference set to compare
  observed `/bmad-auto` behavior against — "did the actual spike-log
  produced on disk match this shape? did resume-skip on a second
  invocation behave like the `resumed` fixture?"

## Source of truth

[SKILL.md Stage 1.f](../../../../skills/bmad-auto/SKILL.md) (lines
~317–355 in the current SKILL.md). The persistence path, three
decision states, and HALT-on-unresolved-block message are quoted from
there verbatim where this README quotes the contract.

Supporting context:

- [docs/auto-skills-design.md](../../../auto-skills-design.md) Principle 10 — "Per-epic SPIKES live inside Phase 1"
- [docs/bmad-auto-design-intent.md](../../../bmad-auto-design-intent.md) §1f and §"SPIKES — where they live"

## Spike-log format

Persisted to `_bmad-output/.run-state/epic-K-spike-log.md` (where `K`
is the epic number — `7` in these fixtures).

### Header

```markdown
# Epic K — Spike triage log

> **Epic:** <one-line epic title from epics.md>
> **Run:** <which invocation this snapshot represents>
> **Triage pass:** <initial | mixed | resumed | ...>
```

The header is human-oriented context; the parser keys on the entry
lines below, not the header.

### Per-item line shape

Each triage entry is a single bullet (multi-line per-item logs are
fine but the leading bullet line carries the parse-keys):

```
- <ISO-8601 timestamp> [DECISION] K-spike-NN — <source-type> (<source-file>): "<unknown text>" — <reason | action | resolution>
```

Required tokens (in order):

1. **Timestamp** — `YYYY-MM-DDTHH:MM:SSZ` (UTC). Lets the resumed run
   distinguish entries from prior runs vs the current run.
2. **Decision** — one of `[DEFER]`, `[BLOCK]`, `[SPIKE]`, or
   `[RESOLVED]`. Bracketed and uppercase. (See decision semantics
   below; `[RESOLVED]` is the resume-protocol completion marker for a
   previously-`[BLOCK]` item.)
3. **Item ID** — `K-spike-NN` where `K` is the epic number and `NN` is a
   2-digit sequence. Stable across runs — the resume protocol matches
   on this ID.
4. **Source-type + source-file** — where the unknown was extracted from
   per Stage 1.d (brief, SPEC.md, epics.md, architecture.md, or the
   1.e SPIKES checklist question).
5. **Unknown text** — verbatim quote of the assumption / open_question
   / gap text.
6. **Reason / action / resolution** — operator-supplied free-text
   explaining the decision. For `[SPIKE]` items, this includes the
   investigation result. For `[BLOCK]`, what's needed to clear it.

### Section markers (resumed snapshots only)

Resumed snapshots use three H2 sections to make the resume protocol
visible:

- `## Carried over from prior run (<timestamp range>)` — items the
  protocol read off disk and preserved without re-prompting. Each
  carries the marker `**[carried over — prior decision preserved]**`
  (or `**[carried over — spike resolution preserved]**`).
- `## Resolved on this run (previously BLOCK, now cleared)` — items
  that were `[BLOCK]` on the prior run and now have a matching
  `[RESOLVED]` entry. Each `[RESOLVED]` entry pairs with the original
  `[BLOCK]` entry via the same item ID.
- `## New items extracted on this run` — items the 1.d/1.e re-walk
  surfaced that weren't in the prior log. Empty section is OK (and
  shown as such in the `resumed` fixture) — Stage 1.d re-extraction
  is idempotent when upstream artifacts haven't drifted.

### Closing trailer

A one-line summary that totals the decisions and signals what Stage
1.f does next:

- All-DEFER or DEFER+SPIKE-resolved → "Phase 1.f proceeds to Stage
  1.g (tracer-bullet readiness)."
- Any unresolved `[BLOCK]` → "Stage 1.f HALTs per SKILL.md:" followed
  by the verbatim HALT message Stage 1.f prints.

## Decision semantics (the three states)

| State | Semantics | Stage 1.f behavior |
| --- | --- | --- |
| `defer` | Dev-safe to proceed at known risk. The unknown does not gate the tracer or the autonomous fanout for this epic; resolve later (often post-epic in retrospective or in a follow-up epic). | Log entry; continue. |
| `block` | Cannot proceed. The unknown gates the tracer story specifically — typically because the tracer needs to exercise a real integration or honor a Critical-level architecture gap that can't be papered over. | Log entry; HALT Phase 1.f with the verbatim message in SKILL.md Stage 1.f. Operator resolves manually and re-invokes. |
| `spike` | Small dedicated investigation kicked off inline. The operator (or `/bmad-auto`) routes to one of the upstream investigation skills (`bmad-technical-research`, `bmad-domain-research`, `bmad-create-architecture`, `bmad-spec` Validate, etc.) from Stage 1.e's action items; the result is appended to the log entry. Once resolved, behaves like a `defer` for resume purposes (already-resolved, skip on re-entry). | Log entry with action + result; continue. |

In **Headless mode**, Stage 1.f classifies all items as `defer` (per
SKILL.md Stage 1.f Headless rule) and proceeds. The Headless variant
of these fixtures would be a degenerate case of `initial` with
auto-`[DEFER]` reasons; see
[digest-dry-render/headless-exit/epic-K-spike-log.md](../digest-dry-render/headless-exit/epic-K-spike-log.md)
for the Stage 4.e digest counterpart.

## Resume protocol

Verbatim from SKILL.md Stage 1.f:

> **Resumable runs:** on re-entry to 1f, read the spike-log first; skip
> already-resolved items.
>
> If any item is [BLOCK] and unresolved: HALT with:
>
> > Blocked unknowns prevent Phase 2 entry:
> > 1. <item 1 text>
> > 2. <item 2 text>
> >
> > Resolve manually (run spike skills) then re-invoke
> > `/bmad-auto --epics K`. The spike-log persists your prior triage.

In practice:

1. On Phase 1.f entry, check `_bmad-output/.run-state/epic-K-spike-log.md`.
2. If absent → fresh triage pass; walk every item from 1.d + 1.e.
3. If present → parse entries. For each item ID:
   - `[DEFER]` → preserve, do not re-prompt
   - `[SPIKE]` with a recorded result → preserve, do not re-prompt
   - `[BLOCK]` without a matching `[RESOLVED]` entry → still
     unresolved; add to the HALT list
   - `[BLOCK]` with a matching `[RESOLVED]` entry (same item ID) →
     treated as resolved; preserve both entries
4. Re-run 1.d extraction. Append any *new* item IDs (i.e. not present
   in the log) to the "New items" section for fresh triage.
5. If any item is still `[BLOCK]` and unresolved → HALT with the
   verbatim message above.
6. Otherwise → proceed to Stage 1.g.

## How the three fixtures map onto a realistic two-invocation lifecycle

| Fixture | Represents | Decisions | Phase 1.f outcome |
| --- | --- | --- | --- |
| `epic-K-spike-log-initial.md` | First `/bmad-auto --prep --epics 7` invocation, optimistic operator pass — all unknowns are dev-safe. | 4 × DEFER | Proceeds to 1.g |
| `epic-K-spike-log-mixed.md` | Same first invocation, realistic operator pass — same epic, same items, but operator engages each item carefully: defers what's dev-safe, runs a spike inline on one item, surfaces one item as a real block. | 3 × DEFER, 1 × SPIKE (resolved), 1 × BLOCK (unresolved) | HALTs; operator exits and resolves the block externally |
| `epic-K-spike-log-resumed.md` | Second `/bmad-auto --epics 7` invocation, after operator resolved the BLOCK (IT provisioned the Okta dev-tenant). Demonstrates the resume protocol: carried-over items preserved, BLOCK now RESOLVED, no re-prompting. | 3 × DEFER (carried), 1 × SPIKE (carried, resolved), 1 × BLOCK → RESOLVED | Proceeds to 1.g |

The three logs share epic context (epic 7 — Okta SSO) and item IDs
(`K-spike-01` through `K-spike-05`); the `mixed` and `resumed`
snapshots cover the same five items in the same order. `initial`
covers only the first four — the fifth item (`K-spike-05` —
login-latency NFR) surfaces in the `mixed` snapshot because the
operator engaged more deeply on Stage 1.e Q3 (domain unknowns) and
that prompt produced an additional candidate. This is realistic:
initial and mixed are two operator passes against the same epic, and
the more thorough pass surfaces more items.

## Epic context (for readers unfamiliar with the example)

Epic 7 is a synthetic but realistic mid-sized epic: **Add SSO via
Okta to the admin console.** Scope: org-level federated identity
(one Okta tenant per customer org); SCIM auto-provisioning is
explicitly out of scope (deferred to epic 8). Stories: 7-1 (tracer —
end-to-end SSO redirect-loop with a single hardcoded org-mapping),
7-2 (org-mapping mechanism), 7-3 (admin UI for tenant onboarding).

The unknowns surface naturally from this scope:

- `K-spike-01` — single-IdP assumption (deferred — multi-IdP is epic 8)
- `K-spike-02` — cookie scoping (deferred — host-only default works)
- `K-spike-03` — org-mapping derivation (spiked — Okta groups claim wins)
- `K-spike-04` — Okta dev-tenant provisioning (blocked — needs IT)
- `K-spike-05` — login-latency NFR threshold (deferred — platform default works for now)

## Format consistency with D5v4 digest-dry-render fixtures

The D5v4 digest scenarios at
[../digest-dry-render/](../digest-dry-render/) include
`epic-K-spike-log.md` files that Stage 4.e reads to render the
`Spike triage: <N deferred + M blocked>` summary line. Those D5v4
fixtures are all minimal (no triage entries; the scenarios assumed
all unknowns resolved during 1d/1e walk-through) and use this header
format:

```markdown
# Epic 3 — Spike triage log

_(Stage 1.f produced no triage entries — all unknowns resolved
directly in 1d/1e walk-through. Empty log persisted so Stage 4.e
can confirm the file existed and render the `0 deferred + 0 blocked`
summary deterministically.)_
```

The header here (`# Epic K — Spike triage log`) matches the D5v4
fixtures verbatim — same H1 shape. The D7v4 fixtures extend with
populated content (entries, sections, decision states); the empty-log
variant in D5v4 remains valid as the "no triage needed" degenerate
case. Stage 4.e's parser can compute its summary line by counting
`[DEFER]` and `[BLOCK]` occurrences across the file; the
`[RESOLVED]` and `[SPIKE]` markers are orthogonal to the digest line
(they don't add to either count once resolved). For the populated
fixtures here, the Stage 4.e digest summary would render as:

- `initial`: `Spike triage: 4 deferred + 0 blocked`
- `mixed`: `Spike triage: 3 deferred + 1 blocked` (the SPIKE is
  resolved and counts as deferred-equivalent; the BLOCK is unresolved
  at the time of digest)
- `resumed`: `Spike triage: 4 deferred + 0 blocked` (the BLOCK
  cleared on this run; the SPIKE resolution preserved)

## Files

- `epic-K-spike-log-initial.md` — first triage pass, all DEFER
- `epic-K-spike-log-mixed.md` — same first run, realistic mix (DEFER + SPIKE + BLOCK)
- `epic-K-spike-log-resumed.md` — second invocation after operator resolved the BLOCK; demonstrates resume protocol
- `README.md` — this file

## Cross-references

- [SKILL.md Stage 1.d](../../../../skills/bmad-auto/SKILL.md) — unknown extraction
- [SKILL.md Stage 1.e](../../../../skills/bmad-auto/SKILL.md) — SPIKES checklist (7 questions; "no" answers route to investigation skills)
- [SKILL.md Stage 1.f](../../../../skills/bmad-auto/SKILL.md) — per-epic spike triage (the spec for this fixture set)
- [SKILL.md Stage 4.e](../../../../skills/bmad-auto/SKILL.md) — digest read of `epic-K-spike-log.md` for the `Spike triage:` summary line
- [docs/auto-skills-design.md](../../../auto-skills-design.md) Principle 10 + Architecture section on resumability
- [docs/bmad-auto-design-intent.md](../../../bmad-auto-design-intent.md) §1f and §"SPIKES — where they live"
- [../digest-dry-render/](../digest-dry-render/) — D5v4 fixtures consuming `epic-K-spike-log.md` at Stage 4.e
- [../halt-detection/](../halt-detection/) — D1v4 HALT fixtures; the unresolved-BLOCK HALT message in 1.f is a separate HALT class from the Stage 3.4 capture-pane triggers but shares the design pattern (HALT-on-doubt, persist context, resume cleanly).
