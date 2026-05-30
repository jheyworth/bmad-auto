# TEA-outputs fixture suite

Snapshot fixtures of known-good outputs from the two BMad TEA (Test
Architect) skills consumed by `/bmad-auto` at end-of-epic:

- **`bmad-testarch-trace`** writes the slim `gate-decision.json`
  consumed by Stage 4.a.
- **`bmad-testarch-nfr`** writes the `nfr-assessment.md` markdown
  report consumed by Stage 4.b.

These fixtures are the regression-detection signal for the
**producer-side drift defense** built in tasks T1-T4 of
[`bmad-auto-testarch-drift-defense.md`](../../build-tasks/bmad-auto-testarch-drift-defense.md).
They catch TEA reformatting drift at development time, before runtime
hits a real operator.

TEA is actively shipped as part of BMad but the producer-side output
schemas are **not pinned upstream**. If TEA reformats outputs in a
future release, `/bmad-auto` silently reads garbage and reports the
wrong verdict in the digest. The three-layer local defense closes that
silent-drift surface:

1. **T1 — Runtime validation** of `gate-decision.json` shape and the
   `gate_status` enum membership in
   [`skills/bmad-auto/SKILL.md`](../../../skills/bmad-auto/SKILL.md)
   Stage 4.a. HALTs loud on drift.
2. **T2 — Canonical sidecar parser** for `nfr-assessment.md` in
   Stage 4.b. Parses the markdown exactly once, writes a clean
   `epic-K-nfr-decision.json` sidecar that downstream stages consume.
   Single point of repair when TEA reformats.
3. **T4 (this directory) — Snapshot fixtures** — committed exemplars
   of the expected output shape across every verdict class. A
   developer comparing current TEA outputs against these fixtures
   catches drift before it reaches a real operator.

## Source-of-truth (verbatim) for the fixture shapes

The fixtures here are not invented from thin air — they mirror the
shapes that TEA's published step files and templates emit today:

- **gate-decision JSON shape:** derived from the slim payload at
  [`/.claude/skills/bmad-testarch-trace/steps-c/step-05-gate-decision.md`](../../../.claude/skills/bmad-testarch-trace/steps-c/step-05-gate-decision.md)
  (around lines 526-541, inside the `if (gateEligible &&
  ['PASS','CONCERNS','FAIL','WAIVED'].includes(gateDecision))` guard).
  Field set: `schema_version`, `evaluated_at`, `repo`, `target`,
  `collection_status`, `gate_basis`, `gate_status`, `rationale`,
  `p0_status`, `p1_status`, `overall_status`, `critical_open`,
  `links`.
- **NFR markdown shape:** derived from the rendered template at
  [`/.claude/skills/bmad-testarch-nfr/nfr-report-template.md`](../../../.claude/skills/bmad-testarch-nfr/nfr-report-template.md).
  The template emits a `## Gate YAML Snippet` section (verbatim
  heading) with a `nfr_assessment.overall_status` field carrying the
  verdict. T2's parser anchors on that section.

**Divergence note (from T2 outcome):** the prose in TEA's
`steps-c/step-05-generate-report.md` calls the structured-status
section "Gate-ready YAML snippet" and refers to a bare `status:`
field. The rendered template at `nfr-report-template.md` actually
emits `## Gate YAML Snippet` (no "Gate-ready" prefix) with
`nfr_assessment.overall_status` (no bare `status:`). The fixtures
here follow the template — the template is what gets rendered into
the markdown that the parser reads. T2's parser handles the
template-shape selector first and falls back to alternative selectors
for older TEA renderings.

## Inventory

### Positive fixtures (happy-path snapshots)

| Fixture | Expected status | Purpose |
| --- | --- | --- |
| `gate-decision-pass.json` | `gate_status: PASS` | All-green epic. P0=MET, P1=MET, overall=MET, `critical_open: 0`. Realistic rationale references the canonical Phase-2 PASS thresholds (P0 100%, P1 ≥90%, overall ≥80%). |
| `gate-decision-concerns.json` | `gate_status: CONCERNS` | P1 in the 80-89% band. `p1_status: PARTIAL`, rationale calls out specific stories (E5.S2, E5.S4) whose ACs lack end-to-end coverage. |
| `gate-decision-fail.json` | `gate_status: FAIL` | Three critical requirements uncovered (`critical_open: 3`), `p0_status: NOT_MET`. Rationale references ATDD-red tests at iteration-budget exhaustion. |
| `gate-decision-waived.json` | `gate_status: WAIVED` | Stakeholder-approved waiver per Rule 6 of the gate-decision logic. `gate_basis: "none"` (the canonical signal that gate thresholds were not applied), with a rationale documenting the waiver, scope, and expiry date. |
| `nfr-assessment-pass.md` | `overall_status: PASS` (in the `## Gate YAML Snippet` block) | All eight ADR categories at PASS or CONCERNS; net verdict PASS. Two CONCERNS-class items tracked as short-term cleanup. |
| `nfr-assessment-concerns.md` | `overall_status: CONCERNS` | Three high-priority items, including a GDPR audit-log retention gap and an unverified streaming-export memory guarantee. Zero FAILs but materially elevated operational risk. |
| `nfr-assessment-fail.md` | `overall_status: FAIL` | Five FAIL-classed categories, three CRITICAL correctness issues (UTC-boundary atomicity, clock-skew tolerance, replay safety). Release blocked. |
| `README.md` | — | This file. |

**Enum coverage (positive):**

- **`gate-decision.json` `gate_status`:** all four values exercised
  (`PASS | CONCERNS | FAIL | WAIVED`).
- **`nfr-assessment.md` `overall_status`:** all three values
  exercised (`PASS | CONCERNS | FAIL`). NFR does NOT emit `WAIVED` —
  that's a trace-only verdict (confirmed in T2 outcome).

### Negative fixtures (drift / corruption exemplars)

Snapshots of the *failure modes* T1 + T2 must reject. Each fixture
exercises one specific validation step in the read pipeline; the
expected outcome is a loud, operator-actionable HALT — never a silent
wrong verdict. The narrative continues the rate-limit / quota world
used in the positive fixtures so the negatives feel like real outputs
that got corrupted in transit, not synthetic stubs.

| Fixture | Driving condition | Expected | Notes |
| --- | --- | --- | --- |
| `gate-decision-missing-status.json` | Valid JSON, `gate_status` key entirely absent. All other canonical fields realistically populated (derived from `gate-decision-pass.json`). | **T1 HALT — field-presence check** ("expected `gate_status` field is missing") | Exercises the third T1 validation step (top-level `gate_status` field present). The file parses cleanly and looks plausible field-by-field, so this is the surface that catches a TEA refactor that renames or relocates the verdict key. |
| `gate-decision-bad-enum.json` | Valid JSON, `gate_status: "pass"` (lowercase). All other fields realistic. | **T1 HALT — enum membership check** ("unrecognized value (`pass`)") | Exercises the fourth T1 validation step (case-sensitive enum membership in `PASS \| CONCERNS \| FAIL \| WAIVED`). See ambiguity flags below — this fixture is load-bearing for confirming the implementation is strict, not tolerant. |
| `gate-decision-malformed.json` | INVALID JSON. Truncated mid-string inside the `rationale` value with no closing quote and no closing brace. Simulates an agent killed mid-`fwrite`. | **T1 HALT — JSON parse failure** (raised before any field check) | Exercises the second T1 validation step (file parses as JSON). Verified `json.load()` raises `JSONDecodeError: Unterminated string starting at line 13 col 16`. The parse error must surface as HALT, never as "treat as missing" or "treat as empty object". |
| `nfr-assessment-no-status.md` | Realistic NFR report body with headers, criteria narrative, evidence tables, recommendations. The entire `## Gate YAML Snippet` section is absent AND no `^Status:` / `^Gate Status:` / `**Gate Status:**` lines appear anywhere in the body. | **T2 HALT — parser cannot locate status** (UNKNOWN classification → HALT per the "HALT-on-UNKNOWN is intentional" picker note) | Exercises T2's terminal HALT branch after both the primary selector (`## Gate YAML Snippet` → `nfr_assessment.overall_status`) and the fallback regex selectors fail. Simulates a TEA template refactor that removed the gate-status surfaces entirely (or a rendering bug that dropped the trailing section). |
| `nfr-assessment-truncated.md` | Realistic frontmatter + first couple of sections, then the `## Gate YAML Snippet` heading opens a ```yaml fence and writes a few fields before cutting off mid-line. No `overall_status:` line, no closing fence, no `**Gate Status:**` line, no further content. Simulates an agent killed mid-write. | **T2 HALT — parser cannot locate status** (UNKNOWN classification → HALT) | Exercises a subtler T2 failure: the primary anchor (`## Gate YAML Snippet` heading) *is* present so the parser descends into the section, but the target field (`overall_status`) was never written and the fallback selectors also find nothing. The parser must not silently substitute `UNKNOWN` or treat the truncated content as `PASS`. |

**T1/T2 step coverage (negative):**

- **T1 step 1 (file exists):** not currently exercised — orchestrator-
  level concern, less likely to drift than format changes. Operator
  may add a `gate-decision-absent` sentinel if the file-missing branch
  needs explicit coverage.
- **T1 step 2 (JSON parses):** `gate-decision-malformed.json`.
- **T1 step 3 (`gate_status` present):** `gate-decision-missing-status.json`.
- **T1 step 4 (enum membership, case-sensitive):** `gate-decision-bad-enum.json`.
- **T2 primary selector failure (`## Gate YAML Snippet` →
  `nfr_assessment.overall_status` absent or section missing):**
  `nfr-assessment-no-status.md` (section missing entirely) and
  `nfr-assessment-truncated.md` (section present, field absent).
- **T2 fallback selectors (`^Status:` / `^Gate Status:` /
  `**Gate Status:**` regex):** both negative markdown fixtures also
  lack these surfaces, so they exercise the full HALT path through
  primary-fails → fallback-fails → UNKNOWN → HALT.

### Ambiguity flags (subtle classification considerations)

- **`gate-decision-bad-enum.json`** — the `gate_status: "pass"` value
  would pass a tolerant parser that case-folds before enum membership
  check. **Confirm T1's implementation is strict** (uppercase-only
  enum check, no `.upper()` / `.casefold()` normalization before the
  membership test). Per the T1 outcome and the canonical source at
  `step-05-gate-decision.md` line 526, TEA emits the enum
  uppercase-only; the case-sensitivity guard is the contract. If a
  future tuning loosens to case-insensitive matching, this fixture
  silently stops exercising the bad-enum branch and the suite needs
  a true bad-enum value (e.g. `"PASSED"` or `"OK"`).
- **`nfr-assessment-truncated.md`** — the `## Gate YAML Snippet`
  heading IS present, but the `overall_status` line is not. A
  sloppy T2 implementation that anchors only on heading-presence
  (without confirming the target field) would incorrectly classify
  this as "parsed" with an empty/null status, then propagate UNKNOWN
  downstream. **Confirm T2's implementation requires the field, not
  just the section.** Per the T2 outcome the parser explicitly reads
  `nfr_assessment.overall_status` from inside the section; this
  fixture is the regression guard against drift toward
  heading-presence-only logic.
- **`gate-decision-malformed.json`** — a tolerant JSON loader (e.g.
  `json5` or a partial-recovery library) might successfully parse
  the truncated content as `{schema_version: ..., ..., gate_status:
  "PASS"}` if it sees the closing `"PASS"` quote before the
  truncation and recovers. **Confirm T1 uses stock `json.load()` /
  equivalent strict parser.** Per T1 the parser is strict and HALTs
  on any `JSONDecodeError`; this fixture is the regression guard
  against drift toward "best-effort" parsing.
- **`nfr-assessment-no-status.md`** — no subtle ambiguity. The status
  surface is absent in every form the T2 parser knows about. A
  passing parser would have to invent a status, which is exactly the
  silent-corruption mode T2 was built to prevent.
- **`gate-decision-missing-status.json`** — no subtle ambiguity. The
  field is absent; `data.get("gate_status")` returns `None`, which is
  not in the enum; HALT fires. Only failure mode is a parser that
  treats absent-field as "default to PASS" — which would be a
  catastrophic implementation bug, not a tuning question.

## Re-snapshot protocol

These fixtures are static. TEA's output shape is not. The protocol
below is the load-bearing operational artifact — fixtures without a
re-snapshot discipline go stale and stop detecting drift.

### When to re-check

**After every `/update-bmad` run.** The `/update-bmad` skill re-clones
the BMAD-METHOD and bmad-builder repos, which can pull updated TEA
skill files. After the update completes:

1. Read the current TEA canonical sources:
   - [`/.claude/skills/bmad-testarch-trace/steps-c/step-05-gate-decision.md`](../../../.claude/skills/bmad-testarch-trace/steps-c/step-05-gate-decision.md)
     (the slim-payload field set, around lines 526-541)
   - [`/.claude/skills/bmad-testarch-nfr/nfr-report-template.md`](../../../.claude/skills/bmad-testarch-nfr/nfr-report-template.md)
     (the rendered structure, especially the `## Gate YAML Snippet`
     section)
   - [`/.claude/skills/bmad-testarch-nfr/steps-c/step-05-generate-report.md`](../../../.claude/skills/bmad-testarch-nfr/steps-c/step-05-generate-report.md)
     (the prose around what the template emits — used to spot drift
     between the prose and the template)
2. Diff the current sources against what these fixtures encode.

### What to look for

- **Field set additions or removals** in the slim `gate-decision.json`
  payload (any field that appears in the current source but not in
  the fixtures, or vice versa).
- **Field rename** (e.g., if `gate_status` is renamed, or if
  `nfr_assessment.overall_status` migrates to a different key).
- **Enum-value changes** for `gate_status` or `overall_status` (e.g.,
  if TEA adds a new verdict class like `WARN` or `BLOCKED`).
- **Section-heading changes** in the NFR template (e.g., if
  `## Gate YAML Snippet` is renamed). The T2 parser anchors on this
  heading.
- **YAML-block structural changes** (e.g., if the `nfr_assessment:`
  parent key changes name).

### What to do when drift is detected

1. **Update the fixtures here** to reflect the new shape — author a
   minimal change to bring each affected fixture into line with the
   current canonical source. Preserve realism (real-looking story
   keys, plausible rationales, etc).
2. **Update T1's validation enum** in
   [`skills/bmad-auto/SKILL.md`](../../../skills/bmad-auto/SKILL.md)
   Stage 4.a if the `gate_status` enum widened or changed.
3. **Update T2's parser** in
   [`skills/bmad-auto/SKILL.md`](../../../skills/bmad-auto/SKILL.md)
   Stage 4.b if the NFR markdown selector changed (section heading,
   YAML key path, or status enum).
4. **Update the cross-references at the top of this README** if the
   canonical source paths moved.
5. **Commit the fixture updates and the SKILL.md changes together**
   so the snapshot and the consumer stay in lockstep.

### What to do when no drift is detected

No action. The fixtures still represent the current shape. Note the
re-check date in your `/update-bmad` session log so the next
operator can see when the most recent verification happened.

### Negative-fixture ongoing-relevance review

The negative fixtures encode specific failure modes against the
*current* T1 + T2 implementation. When TEA's schema changes — or
when T1 / T2 themselves are tuned in response — some negatives may
silently stop exercising the branch they were authored for. After
every `/update-bmad` re-check (above), walk the negative inventory
and confirm each fixture still reaches the HALT class its row in the
inventory claims:

- **If TEA case-folded the `gate_status` enum** (e.g. accepted both
  `"PASS"` and `"pass"`) and T1 was tuned to match,
  `gate-decision-bad-enum.json` would no longer exercise the
  case-sensitivity guard. Replace its `gate_status` value with a true
  unknown enum value (e.g. `"PASSED"` or `"OK"`) so the suite
  continues to exercise the enum-membership branch.
- **If TEA added a structured machine-readable status sidecar**
  alongside `nfr-assessment.md` (e.g. `nfr-decision.json` produced by
  TEA directly, mirroring the trace pattern) and T2 was retargeted to
  read the sidecar instead of grepping the markdown,
  `nfr-assessment-no-status.md` and `nfr-assessment-truncated.md`
  would become irrelevant — the markdown is no longer the parser's
  input. Replace them with `nfr-decision-*.json` negatives mirroring
  the gate-decision shape.
- **If TEA renamed `gate_status`** (e.g. to `verdict` or
  `gate_decision`), `gate-decision-missing-status.json` would
  technically still exercise "absent expected field" but the field
  name in the row description and ambiguity-flag prose needs updating
  alongside the T1 validation update.
- **If TEA's JSON output got wrapped in an envelope** (e.g. `{ "data":
  { "gate_status": ... } }`), `gate-decision-malformed.json`'s
  truncation point may need to move to remain a realistic
  agent-killed-mid-write simulation rather than an obvious
  envelope-break.
- **If T2 was tuned to be tolerant of missing status** (e.g. defaulted
  to `CONCERNS` rather than HALTing on UNKNOWN), both negative
  markdown fixtures would silently stop exercising the HALT path.
  This would be a regression in the drift-defense posture and should
  trigger a discussion before the fixtures are updated to reflect the
  new behavior.

Apply the same "commit fixture updates + SKILL.md changes together"
discipline from the drift-detected section above. The negative
fixtures and the validation logic they regression-test must stay in
lockstep.

### What NOT to do

- **Do not update the fixtures speculatively** ahead of a TEA change.
  The fixtures are a snapshot of the *current* canonical shape;
  ahead-of-time updates would defeat their drift-detection purpose.
- **Do not delete a fixture because its verdict class feels
  redundant.** All `gate_status` and `overall_status` enum values
  have a dedicated fixture by design — losing a verdict class blinds
  the suite to drift in that branch.
- **Do not skip the re-check** after `/update-bmad`. The whole point
  of this suite is to catch drift at development time; skipping the
  re-check defers detection to runtime, which is the failure mode
  T1-T4 exist to prevent.

## Cross-references

### Consumers of the fixture shapes

- **T1 — Stage 4.a read-side validation** (gate-decision JSON):
  [`skills/bmad-auto/SKILL.md`](../../../skills/bmad-auto/SKILL.md)
  Stage 4.a, "Read-side validation (runtime drift guard)" block.
  Validates file existence, JSON parse, presence of `gate_status`,
  and enum membership in `PASS | CONCERNS | FAIL | WAIVED`.
- **T2 — Stage 4.b canonical sidecar parser** (NFR markdown):
  [`skills/bmad-auto/SKILL.md`](../../../skills/bmad-auto/SKILL.md)
  Stage 4.b, "Post-invocation parse → canonical sidecar (drift
  containment)" block. Anchors on the `## Gate YAML Snippet` section
  and the `nfr_assessment.overall_status` field; falls back to
  alternative selectors before HALTing.
- **T3 — Stage 4.e digest composition:**
  [`skills/bmad-auto/SKILL.md`](../../../skills/bmad-auto/SKILL.md)
  Stage 4.e. Reads the T2 sidecar for the NFR verdict; never
  re-parses the markdown. Surfaces `evidence_summary` from the
  sidecar when present.

### Canonical TEA sources (the shape this suite snapshots)

- [`/.claude/skills/bmad-testarch-trace/steps-c/step-05-gate-decision.md`](../../../.claude/skills/bmad-testarch-trace/steps-c/step-05-gate-decision.md)
  — the slim `gate-decision.json` payload definition lives around
  lines 526-541. The full `e2e-trace-summary.json` payload (lines
  414-498) is a superset; the slim version is what `/bmad-auto`
  consumes.
- [`/.claude/skills/bmad-testarch-nfr/nfr-report-template.md`](../../../.claude/skills/bmad-testarch-nfr/nfr-report-template.md)
  — the rendered markdown template. The `## Gate YAML Snippet`
  section starts around line 388.
- [`/.claude/skills/bmad-testarch-nfr/steps-c/step-05-generate-report.md`](../../../.claude/skills/bmad-testarch-nfr/steps-c/step-05-generate-report.md)
  — the report-generation step prose. Useful for catching prose-vs-
  template drift (the prose refers to "Gate-ready YAML snippet"
  while the template emits "Gate YAML Snippet" — track both).

### Related artifacts in this repo

- [`bmad-auto-testarch-drift-defense.md`](../../build-tasks/bmad-auto-testarch-drift-defense.md)
  — the build task list that authored T1-T5 (this fixture suite is T4).
- [`skills/bmad-auto/test-fixtures/halt-detection/README.md`](../halt-detection/README.md)
  — sister fixture suite for the HALT-detection heuristic. This
  suite mirrors its inventory-table + protocol conventions.
- [`skills/bmad-auto/references/README.md`](../../../skills/bmad-auto/references/README.md)
  — the known-limitations note that T5 updates to reflect the
  three-layer local defense.

## Fixture count summary

- **Positive fixtures (happy-path snapshots):** 7
  - `gate-decision-pass.json`, `gate-decision-concerns.json`,
    `gate-decision-fail.json`, `gate-decision-waived.json`
  - `nfr-assessment-pass.md`, `nfr-assessment-concerns.md`,
    `nfr-assessment-fail.md`
- **Negative fixtures (drift / corruption exemplars):** 5
  - `gate-decision-missing-status.json`,
    `gate-decision-bad-enum.json`, `gate-decision-malformed.json`
  - `nfr-assessment-no-status.md`, `nfr-assessment-truncated.md`

**Total fixtures: 12** (excluding this README).

**T1 validation-step coverage:** 3 of the 4 T1 steps have a dedicated
negative fixture (parse, field-presence, enum-membership). The
file-exists step is not currently exercised by a fixture — see the T1
step-coverage note in the negative inventory above.

**T2 selector coverage:** both the primary selector failure
(`## Gate YAML Snippet` → `nfr_assessment.overall_status` missing,
two flavors: section-absent and section-present-field-absent) and the
full HALT-on-UNKNOWN path (primary + fallback selectors all fail) are
exercised.

## Provenance

Authored 2026-05-26 by T4 of the
`bmad-auto-testarch-drift-defense` build task list. Field sets
verified against TEA canonical sources on the same date; if the TEA
team moves the canonical sources or restructures the slim payload /
template, the cross-references above need updating alongside the
fixtures themselves.

Negative fixtures added 2026-05-26 as a follow-up to T4 (post-merge),
extending the suite from happy-path-only (7 fixtures) to combined
happy-path + drift-defense (12 fixtures). The negatives encode the
specific failure modes T1 + T2 must reject and serve as
regression-detection signal for any future tuning of the validation
logic. Canonical-source field set re-verified on the same date
(`step-05-gate-decision.md` lines 526-541 — enum still
`['PASS','CONCERNS','FAIL','WAIVED']` case-sensitive;
`nfr-report-template.md` `## Gate YAML Snippet` heading and
`nfr_assessment.overall_status` field both unchanged) — no TEA
canonical drift since the T4 snapshot.
