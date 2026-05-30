# Quality-gate truth-table fixtures (D8v4)

Six fixtures exercising the Phase 4 quality-gate combined-decision truth table:
the load-bearing v4 quality contract that runs at the end of every non-HALT
epic and decides whether to PROCEED, BLOCK, or PROCEED with documented risk.

This set is the structured-JSON sibling to D5v4's plain-text `.txt` summary
files under `skills/bmad-auto/test-fixtures/digest-dry-render/`. See
**Artifact-shape contract** below for the split.

## Why this fixture set exists

1. **G1 contract review.** G1 operator review of D8v4 needs concrete examples
   covering each truth-table cell so the combined logic in SKILL.md and the
   `gate-decision.json` schema in `bmad-testarch-trace` can be sanity-checked
   together against real outputs.
2. **Stage 4.e digest input.** D5v4's digest dry-renders consume the plain-text
   summaries (`epic-K-trace-gate.txt`, `epic-K-nfr-gate.txt`). The `.json`
   artifacts here document what `bmad-testarch-trace` / `bmad-testarch-nfr`
   would have produced before the orchestrator reduced them to a one-token
   `.txt` sidecar.
3. **Regression baseline for D14v4 / D11v4 tuning.** When G3v4/G4v4 surfaces
   gate-decision drift, downstream tuning tasks can diff observed JSON against
   these six fixtures to localize the drift.

## Source-of-truth references

- **`SKILL.md (Stage 4.a/4.b)`** — definitive contract for
  `bmad-testarch-trace` (lines 100–128) and `bmad-testarch-nfr`
  (lines 132–144), plus the combined-decision truth table
  (lines 148–162). The `gate-decision.json` schema fields used here are
  quoted from the *Schema (verbatim)* block at lines 122–126.
- **`skills/bmad-auto/SKILL.md`** — Stage 4.a (lines 637–650, trace gate),
  Stage 4.b (lines 652–663, NFR gate), Stage 4.e (lines 721–777, digest).
  The combined logic block is in the investigation doc (above); SKILL.md
  records only the per-stage outputs that feed it.
- **D5v4 digest scenarios** — three digest dry-renders consume these gate
  decisions:
  - `skills/bmad-auto/test-fixtures/digest-dry-render/natural-exit-v4/` —
    PASS + PASS → PROCEED cleanly
  - `skills/bmad-auto/test-fixtures/digest-dry-render/quality-gate-fail/` —
    CONCERNS + FAIL → BLOCK
  - `skills/bmad-auto/test-fixtures/digest-dry-render/quality-gate-waived/` —
    WAIVED + PASS → PROCEED (with documented risk)

## The truth table

Per `SKILL.md (Stage 4.a/4.b)` lines 148–162 (verbatim):

```
trace.gate_status: PASS | CONCERNS | FAIL | WAIVED
nfr.gate_status:   PASS | CONCERNS | FAIL  (only if implementation evidence exists)

IF trace == FAIL                                       → BLOCK merge, escalate to operator
ELSE IF trace == CONCERNS AND nfr == FAIL              → BLOCK, escalate
ELSE IF (trace == PASS OR CONCERNS) AND
        (nfr == PASS OR CONCERNS OR N/A)               → Proceed to digest, operator reviews
ELSE IF trace == WAIVED                                → Proceed with documented risk
```

Expanded as a matrix (rows = trace, cols = NFR):

| trace ↓ / NFR → | **PASS** | **CONCERNS** | **FAIL** | **N/A** |
|---|---|---|---|---|
| **PASS** | PROCEED *(cell 1)* | PROCEED | PROCEED *(combined-logic gap — see note)* | PROCEED *(cell 6)* |
| **CONCERNS** | PROCEED with operator decision *(cell 2)* | PROCEED with operator decision | **BLOCK** *(cell 4)* | PROCEED with operator decision |
| **FAIL** | **BLOCK** *(cell 3 — NFR short-circuited)* | **BLOCK** | **BLOCK** | **BLOCK** |
| **WAIVED** | PROCEED with documented risk *(cell 5)* | PROCEED with documented risk | PROCEED with documented risk | PROCEED with documented risk |

**Combined-logic gap to surface at G1:** The verbatim contract handles
`PASS + FAIL` only implicitly — it falls through the second ELSE IF
(`trace==CONCERNS AND nfr==FAIL`) and lands in the third ELSE IF
(`(trace == PASS OR CONCERNS) AND (nfr == PASS OR CONCERNS or N/A)`)
**without matching, because nfr==FAIL isn't in that PASS/CONCERNS/N/A set**.
The contract as written drops through to `trace == WAIVED`, which also
doesn't match. Strict reading: no decision returned. Likely-intended
reading: `PASS + FAIL → BLOCK` (NFR failure is BLOCKing regardless of
trace strength). **Flag for G1: confirm intent and tighten the contract
text in `SKILL.md (Stage 4.a/4.b)`.** This gap is the
reason the cell set below covers six discrete decisions and not the
fuller 4×4 matrix — we don't want to encode a fixture for an ambiguous
contract path.

## Artifact-shape contract

Two related artifact types exist for each gate, and this set documents
their relationship:

| Artifact | Producer | Shape | Consumer |
|---|---|---|---|
| `gate-decision.json` (trace) | `bmad-testarch-trace` | structured JSON (this dir) | this dir + Stage 4.e digest reads the summary derived from it |
| `nfr-gate-decision.json` | `bmad-testarch-nfr` | structured JSON (this dir) | this dir + Stage 4.e digest reads the summary derived from it |
| `epic-K-trace-gate.txt` | `/bmad-auto` Stage 4.a step 3 | plain-text, line 1 = verdict, optional line 2 = `Reason: <...>` | Stage 4.e digest (read directly) |
| `epic-K-nfr-gate.txt` | `/bmad-auto` Stage 4.b step 3 | same plain-text shape | Stage 4.e digest (read directly) |

**Why both:** SKILL.md Stage 4.a says *"Record the gate status (PASS /
CONCERNS / FAIL / WAIVED) to `_bmad-output/.run-state/epic-K-trace-gate.txt`."*
Stage 4.e digest reads the `.txt` sidecar (not the full JSON) for one-screen
rendering. The structured JSON remains the authoritative artifact under
`_bmad-output/implementation-artifacts/epic-K-gate-decision.json` — operators
clicking through from the digest land in the full report. **D5v4 fixed the
plain-text shape; D8v4 fixes the structured JSON shape. They must round-trip
deterministically — the `.txt` verdict on line 1 must equal `gate_status` in
the matching `.json`, and any `Reason:` line should be derivable from the
JSON's blockers/recommendations/gap_analysis content.** Each cell below
honors that round-trip.

## `gate-decision.json` schema fields used

Per `SKILL.md (Stage 4.a/4.b)` line 122 *"Schema (verbatim)"*:

- `coverage_statistics` (total_requirements, fully_covered, partially_covered,
  uncovered, overall_coverage_pct, priority_breakdown, by_level)
- `gap_analysis` (critical_gaps, high_gaps, medium_gaps, low_gaps)
- `gate_criteria` (p0_coverage_required/actual/status,
  p1_coverage_target/minimum/actual/status,
  overall_coverage_minimum/actual/status)
- `blockers` and `recommendations`

Plus the meta fields invented for fixture traceability (not part of the
canonical schema; prefixed with `$` to make this clear): `$artifact`,
`$producer`. Plus a top-level `gate_status` (the contract names it but
doesn't include it in the *Schema (verbatim)* block — likely-implicit; flag
for G1) and `decision_mode` (named in the contract at line 120 as
`decision_mode=deterministic`). The WAIVED cell adds a `waiver` block
(author, recorded_at, rationale, scope_note) — not enumerated in the
contract; **fixture decision documented below**.

The `nfr-gate-decision.json` shape is not enumerated in the investigation
doc beyond "PASS/CONCERNS/FAIL with evidence-based justification" (line 142).
The shape used here mirrors the trace contract: `gate_status`,
`evidence_summary` (broken out by performance / security / reliability /
maintainability), `blockers`, `recommendations`. **Flag for G1: this shape
needs codification once `bmad-testarch-nfr` is observed in a real run.**

## The 6 cells

### Cell 1 — `trace-pass-nfr-pass`

> **Truth-table position:** trace=PASS, NFR=PASS → PROCEED
> (digest renders cleanly, no operator action required beyond normal review)
>
> **Couples with D5v4:** `digest-dry-render/natural-exit-v4/` (same shape;
> the D5v4 `.txt` sidecars there match what the digest reads from this cell's
> JSON via the artifact-shape contract above).

Files:
- `trace-pass-nfr-pass.json` — gate-decision.json (trace, PASS)
- `trace-pass-nfr-pass-nfr.json` — nfr-gate-decision.json (NFR, PASS)
- `trace-pass-nfr-pass-trace-summary.txt` — plain-text sidecar (`PASS`)
- `trace-pass-nfr-pass-nfr-summary.txt` — plain-text sidecar (`PASS`)

Epic context (implicit; same across cells 1, 2, 4): epic 3 "Inbound rate
limiting + onboarding hardening" — three stories, customer-facing, all
five NFR dimensions in scope. 17 requirements; tracer-architecture
defines the contract; benchmarks under burst load are evidence.

### Cell 2 — `trace-concerns-nfr-pass`

> **Truth-table position:** trace=CONCERNS, NFR=PASS → PROCEED with
> operator decision required (the CONCERNS verdict surfaces in the digest;
> operator decides whether to merge as-is or fix the partial coverage first).
>
> **Couples with D5v4:** no dedicated D5v4 scenario covers this exact
> combination — `quality-gate-fail/` covers CONCERNS + FAIL; this cell
> exercises the PROCEED-with-CONCERNS branch the D5v4 set lacks. Useful
> for D14v4 regression coverage when a real run lands here.

Files:
- `trace-concerns-nfr-pass.json` — three documented coverage gaps
  (one p1 high, two p1 medium); `p1_coverage_status: CONCERNS`;
  overall coverage still passes its 75% floor
- `trace-concerns-nfr-pass-nfr.json` — perf, security, reliability,
  maintainability all PASS
- `trace-concerns-nfr-pass-trace-summary.txt` — verdict + 3-gap reason
- `trace-concerns-nfr-pass-nfr-summary.txt` — `PASS`

### Cell 3 — `trace-fail`

> **Truth-table position:** trace=FAIL → BLOCK (short-circuits before NFR
> even runs — per the verbatim contract first IF).
>
> **No NFR artifact by design.** The combined-logic contract halts at
> `trace == FAIL` without consulting NFR. The D5v4 set has no equivalent
> scenario (digest dry-render didn't model the trace=FAIL exit). If
> D5v4 gains a `trace-fail/` scenario in a future iteration, the JSON
> here is the canonical input.
>
> **Couples with D5v4:** none directly. Test-only fixture for the
> short-circuit path.

Files:
- `trace-fail.json` — three p0 critical gaps + two p1 high gaps;
  `p0_coverage_status: FAIL` (50% actual vs 100% required);
  overall 52.9% vs 75% minimum; explicit `blockers[]` populated;
  `recommendations[]` calls out the tests-first violation
- `trace-fail-trace-summary.txt` — verdict + critical-gap reason

NFR artifacts intentionally absent — short-circuit, per truth-table
position. The corresponding `.txt` sidecar for NFR would not be written
to `_bmad-output/.run-state/` in a real run either (Stage 4.b only
records when invoked).

### Cell 4 — `trace-concerns-nfr-fail`

> **Truth-table position:** trace=CONCERNS, NFR=FAIL → BLOCK (combined verdict).
>
> **Couples with D5v4:** **direct match.**
> `digest-dry-render/quality-gate-fail/epic-K-trace-gate.txt`
> and `epic-K-nfr-gate.txt` contain the exact same plain-text content
> as this cell's `-trace-summary.txt` and `-nfr-summary.txt` files —
> verified byte-for-byte against D5v4's existing fixtures. The expected
> digest at `quality-gate-fail/expected-digest.md` is what consumes these
> sidecars; the structured JSON here is the upstream from which those
> sidecars derive.

Files:
- `trace-concerns-nfr-fail.json` — two p1 high gaps (3-2 AC-4
  reset-boundary edge case + 3-3 AC-5 tier-aware upgrade flow); p0
  perfect, overall 92%; `p1_coverage_status: CONCERNS` (75% vs 80% min)
- `trace-concerns-nfr-fail-nfr.json` — `gate_status: FAIL`; perf
  budget violated (rate-limiter p99 142ms vs 80ms budget); reliability
  CONCERNS (tail behaviour unverified); security + maintainability PASS;
  explicit blocker populated
- `trace-concerns-nfr-fail-trace-summary.txt` — `CONCERNS` + AC-4/AC-5
  reason
- `trace-concerns-nfr-fail-nfr-summary.txt` — `FAIL` + p99 reason

### Cell 5 — `trace-waived`

> **Truth-table position:** trace=WAIVED → PROCEED with documented risk.
> The WAIVED verdict is operator-driven (not deterministic from coverage
> alone) — it's an explicit decision to accept partial coverage with a
> recorded rationale.
>
> **Couples with D5v4:** **direct match.**
> `digest-dry-render/quality-gate-waived/epic-K-trace-gate.txt` contains
> the exact same plain-text content as this cell's `-trace-summary.txt`
> — byte-for-byte. The structured JSON here adds the `waiver` block
> (author, timestamp, rationale, scope_note) the .txt sidecar can't
> express. The digest's "Decision log entry" line (line 30 of D5v4's
> `quality-gate-waived/expected-digest.md`) is the operator-readable
> projection of this JSON's `waiver` block.

Files:
- `trace-waived.json` — `gate_status: WAIVED` + `waiver` block with
  author, recorded_at, rationale, scope_note. Coverage statistics
  show the underlying numbers that would have produced a FAIL without
  the waiver (44.4% overall, 0% p1) — the waiver explains *why* this
  is acceptable for this epic
- `trace-waived-nfr.json` — `gate_status: PASS`; NFR thresholds tuned
  for internal-tool context (admin latency 500ms budget, single-tenant)
- `trace-waived-trace-summary.txt` — `WAIVED` + rationale verbatim
  from D5v4's match
- `trace-waived-nfr-summary.txt` — `PASS`

Epic context (different from cells 1/2/4): epic 3 "Internal admin tool —
onboarding scaffold" — internal-only, single-tenant, behind SSO. This is
why the WAIVER rationale ("no external API surface, single-tenant
deployment") is legitimately defensible.

**Schema decision worth flagging:** the `waiver` block (author /
recorded_at / rationale / scope_note) is **not** in the
`SKILL.md (Stage 4.a/4.b)` *Schema (verbatim)* enumeration. It's
load-bearing for WAIVED's provenance (who authorized it, when, why) —
flag for G1 to add to the contract. Without this block, a WAIVED
verdict would be unaccountable.

### Cell 6 — `trace-pass-nfr-na`

> **Truth-table position:** trace=PASS, NFR=N/A → PROCEED. N/A is the
> Stage 4.b skip path: *"Skip if no NFR-touching code in the epic diff."*
> (SKILL.md line 654).
>
> **Couples with D5v4:** indirect — no D5v4 scenario currently exercises
> NFR=N/A explicitly, but the digest contract at SKILL.md line 750
> renders `NFR audit: <PASS | CONCERNS | FAIL | N/A>`, so this cell is
> the canonical input for that token.

Files:
- `trace-pass-nfr-na.json` — small epic (8 requirements), 100%
  coverage, all gate criteria PASS
- `trace-pass-nfr-na-trace-summary.txt` — `PASS`
- `trace-pass-nfr-na-nfr-summary.txt` — `N/A` + reason (no
  NFR-touching code; Stage 4.b skipped)

No `nfr-gate-decision.json` artifact — Stage 4.b never invoked
`bmad-testarch-nfr`, so the structured JSON doesn't exist. Only the
`.txt` sidecar exists, and its purpose is to record the skip-decision
for digest rendering.

Epic context: epic 3 "Documentation refresh + internal CLI ergonomics" —
docs-only changes + a CLI prompt-string refactor; no behaviour change to
production code paths, so no NFR-touching diff.

## Round-trip verification

The plain-text summary files should be derivable from the JSON files. Spot-
check:

| Cell | JSON gate_status | .txt line 1 | Match |
|---|---|---|---|
| `trace-pass-nfr-pass` | `PASS` / `PASS` | `PASS` / `PASS` | yes |
| `trace-concerns-nfr-pass` | `CONCERNS` / `PASS` | `CONCERNS` / `PASS` | yes |
| `trace-fail` | `FAIL` / (no NFR JSON) | `FAIL` / (no NFR .txt) | yes |
| `trace-concerns-nfr-fail` | `CONCERNS` / `FAIL` | `CONCERNS` / `FAIL` | yes (matches D5v4 byte-for-byte) |
| `trace-waived` | `WAIVED` / `PASS` | `WAIVED` / `PASS` | yes (matches D5v4 byte-for-byte) |
| `trace-pass-nfr-na` | `PASS` / (skip-decision) | `PASS` / `N/A` | yes |

## Naming convention

`<cell-name>.json` is always the trace artifact (the truth table's primary
axis). NFR artifacts and summaries are suffixed:

- `<cell-name>.json` → trace gate-decision.json
- `<cell-name>-nfr.json` → NFR gate-decision.json (absent for cell 3, cell 6)
- `<cell-name>-trace-summary.txt` → trace plain-text sidecar
- `<cell-name>-nfr-summary.txt` → NFR plain-text sidecar (absent for cell 3)

This keeps related artifacts visually adjacent in a sorted `ls`.

## What this set does NOT cover

- **Real `bmad-testarch-trace` invocation evidence.** The skill has not
  been observed in a real `/bmad-auto` run yet (G4v4 is to-do); the JSON
  shape here is a faithful projection of the documented contract but a
  real run may reveal field-name drift. Tune at D14v4 if observed.
- **NFR JSON schema validation.** The `nfr-gate-decision.json` shape
  used here is invented (mirroring the trace shape). Codify after G4v4
  observation of `bmad-testarch-nfr`.
- **The 4×4 full matrix.** Six cells, not sixteen. The combined-logic
  contract's `PASS + FAIL` gap (see *The truth table* above) means the
  contract is under-specified for some matrix cells; G1 review should
  resolve the gap before fixtures expand.
- **Multi-epic / multi-run interaction.** All six cells use a single
  epic 3 narrative. Cross-epic waiver-scope behaviour (the `scope_note`
  field in the WAIVED block) is documented as fixture metadata but not
  exercised.

## Cross-references

- `SKILL.md (Stage 4.a/4.b)` — `bmad-testarch-trace` +
  `bmad-testarch-nfr` contracts + combined-decision truth table
- `skills/bmad-auto/SKILL.md` — Stage 4.a, 4.b, 4.e
- `skills/bmad-auto/test-fixtures/digest-dry-render/natural-exit-v4/` — Cell 1 consumer
- `skills/bmad-auto/test-fixtures/digest-dry-render/quality-gate-fail/` — Cell 4 consumer
- `skills/bmad-auto/test-fixtures/digest-dry-render/quality-gate-waived/` — Cell 5 consumer
- `bmad-auto-validate-v4.md` — D8v4 entry + downstream
  consumers (G1, D11v4, D14v4)
