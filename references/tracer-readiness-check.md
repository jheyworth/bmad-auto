# Tracer-readiness check

This reference defines the contract that `bmad-auto-dev` (and,
eventually, `bmad-auto-prep`) relies on before treating an epic as "ready to
fan out". A tracer is the first story of an epic (`epic-K story-1`), implemented
end-to-end so that all subsequent stories in the epic have a concrete pattern
to follow. The check below confirms that the tracer story is genuinely
complete *and* that the distillation document(s) it produced are present and
populated.

## Contract

### Format detection precedence

Two contract formats are accepted: **Format A** (per-epic micro-docs) and
the **Format A-equivalent short-circuit** (whole-project artifacts, the
common case under `/bmad-auto`'s single-epic-per-invocation posture).
The check prefers Format A when its per-epic micro-doc markers are
present; otherwise it falls through to the Format A-equivalent
short-circuit. Both formats produce identical downstream behavior: same
pass/fail signal, same tracer artifacts available to Mode Detection and
Launch. Reporting wording always names which format was detected and used
so an operator can tell at a glance which contract shape the epic is on.

> **Note on previously-hedged "Format B".** Earlier revisions of this
> reference hedged against a hypothetical per-epic folder structure
> (`epics/<K>/solution-design.md`) under a "Format B" label. BMAD-METHOD
> v6.8.0 has not signaled this direction — a fresh upstream clone shows
> zero hits for `solution-design` / `solution_design` in `src/`, and the
> v6.8.0 roadmap points toward an **architecture spine** streamline
> (single, flatter `architecture.md`), not per-epic folders. Format B
> logic has therefore been removed; the contract is now dual-format
> (A + A-equivalent).

### Format A (legacy — per-epic micro-docs)

For each epic `K` under consideration, three artifacts must exist:

1. `sprint-status.yaml`: `development_status[{epic-K story-1 key}]` = `done`
   (e.g. `1-1-data-model: done`).
2. `_bmad-output/implementation-artifacts/epic-K-micro-prd.md` exists with
   sections: `Intent`, `Scope`, `Non-goals`, `User-facing surface`,
   `Open questions`.
3. `_bmad-output/implementation-artifacts/epic-K-micro-architecture.md` exists
   with sections: `Architecture decisions`, `Patterns established`,
   `Conventions`, `Integration points`, `Gotchas / footguns`.

These three files are the authoritative tracer-readiness contract under
Format A. Any consumer that needs to decide "can I safely fan out the
remaining stories of epic K?" answers that question by validating all three.

**Producer note:** no BMAD skill currently emits these per-epic micro-docs
automatically. Format A passes only when the operator (or an explicit Stage
2.b producer directive) has authored them. For unmodified BMAD toolchains,
the gate falls through to the Format A-equivalent short-circuit below.

### Format A-equivalent — whole-project short-circuit (default for single-epic projects)

`/bmad-auto`'s design non-negotiable is single-epic-per-invocation
(`docs/auto-skills-design.md` principle #6). In this common case, the
whole-project architecture and SPEC already encode the same
intent/scope/patterns/conventions material that per-epic micro-docs
duplicate. Requiring per-epic micro-docs in that case is paperwork
without value.

For each epic `K`, three artifacts must exist:

1. `sprint-status.yaml`: `development_status[{epic-K story-1 key}]` = `done`
   (as Format A check 1).
2. Whole-project architecture file present at
   `_bmad-output/planning-artifacts/architecture.md` with frontmatter
   `status: 'complete'` AND `stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]`
   (same gate Stage 1.a applies). This file acts as the Format-A
   `epic-K-micro-architecture.md` equivalent for epic K.
3. Whole-project SPEC file present at `_bmad-output/specs/spec-*/SPEC.md`
   (any spec under the spec-* glob, conventionally the most recent)
   OR a PRD at `_bmad-output/planning-artifacts/prds/*/prd.md`. This file
   acts as the Format-A `epic-K-micro-prd.md` equivalent for epic K.

Section-level structural checks (the five Format-A micro-PRD headers + five
micro-architecture headers) are NOT applied here — the whole-project
artifacts use the BMAD canonical section names from `bmad-spec` /
`bmad-create-architecture`, not the micro-doc section names. Presence +
frontmatter completeness are sufficient. The substance check is the
operator-confirmation step ("Does this look like a real tracer? [y/N]").

## Check logic

The check is performed per epic. For epic `K`:

### 0. Format detection (run first)

Before running any per-format checks, decide which format to use. Order is
A → A-equivalent (whole-project short-circuit). The first format whose
markers are present wins; the other is ignored.

- **Format A markers**:
  - `_bmad-output/implementation-artifacts/epic-K-micro-prd.md` exists, AND
  - `_bmad-output/implementation-artifacts/epic-K-micro-architecture.md` exists.
- If **both** Format A markers exist → run the **Format A checks**
  (steps 1, 2, and 3 below).
- Else → run the **Format A-equivalent (whole-project short-circuit)
  checks** (steps EQ.1, EQ.2, and EQ.3 below). This is the default fall-
  through for single-epic projects under unmodified BMAD toolchains.

Record which format was selected so reporting wording can name it
(e.g. `Format A detected at epic-3-micro-prd.md + epic-3-micro-architecture.md`,
or `Format A-equivalent: whole-project architecture.md + SPEC.md`).

### Format A checks

(Run when both Format A per-epic micro-doc markers are present.)

#### 1. Sprint-status check

- Open `sprint-status.yaml`.
- Locate the `development_status` map.
- Find the key corresponding to epic `K`'s first story (conventionally
  `{K}-1-<slug>`, e.g. `1-1-data-model`). The key is the first entry whose
  identifier starts with `{K}-1-`.
- The value of that key must be the exact string `done`.

#### 2. Micro-PRD file check

- Confirm the file
  `_bmad-output/implementation-artifacts/epic-K-micro-prd.md` exists and is
  readable.
- Parse its markdown headers. The following section headers must all be
  present and each section must be non-empty:
  - `## Intent`
  - `## Scope`
  - `## Non-goals`
  - `## User-facing surface`
  - `## Open questions`

#### 3. Micro-architecture file check

- Confirm the file
  `_bmad-output/implementation-artifacts/epic-K-micro-architecture.md` exists
  and is readable.
- Parse its markdown headers. The following section headers must all be
  present and each section must be non-empty:
  - `## Architecture decisions`
  - `## Patterns established`
  - `## Conventions`
  - `## Integration points`
  - `## Gotchas / footguns`

### Format A-equivalent (whole-project short-circuit) checks

(Run when Format A per-epic micro-doc markers are not present. This is the
default for single-epic projects under unmodified BMAD toolchains, since
no BMAD skill currently produces per-epic micro-docs.)

#### EQ.1. Sprint-status check

Identical to Format A check 1 (story-1 key value is `done`).

#### EQ.2. Whole-project architecture file check

- Confirm `_bmad-output/planning-artifacts/architecture.md` exists and is
  readable.
- Parse its YAML frontmatter (the block delimited by `---` lines at the top
  of the file).
- Frontmatter must contain:
  - `status: 'complete'` (case-sensitive exact match; either single-quoted,
    double-quoted, or bare `complete`)
  - `stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]` (the full canonical 8-step
    set; order-insensitive, but all eight integers must be present)

#### EQ.3. Whole-project SPEC (or PRD) file check

- Confirm at least one of the following exists and is readable:
  - `_bmad-output/specs/spec-*/SPEC.md` (per the new flat
    `bmad-spec`-customized convention; first lexicographic match if
    multiple)
  - `_bmad-output/planning-artifacts/prds/*/prd.md` (legacy PRD layout)
- No frontmatter `status` requirement (SPEC frontmatter varies; PRD has
  no canonical status field). Presence + readability are sufficient.

**No section-level checks for EQ.2/EQ.3.** The Format-A micro-doc section
names (`## Intent`, `## Architecture decisions`, etc.) do not match the
canonical section names that `bmad-spec` and `bmad-create-architecture`
emit, and forcing section-name parity would constrain upstream skills
the gate doesn't own. Presence + frontmatter-completeness on architecture
is the structural floor; the substance check is the operator-confirmation
step ("Does this look like a real tracer? [y/N]").

### Section-existence rule

A section is considered present when the exact header line (e.g. `## Intent`)
appears in the document **and** the section body — the lines between this
header and the next header of equal-or-shallower depth, or end-of-file —
contains at least one non-whitespace character. A header with no body counts
as a failure for that section.

The epic is tracer-ready only when all checks for the selected format pass
(all three Format A checks, or all three Format A-equivalent checks).

## Failure modes

Each check has a distinct, actionable failure to report. Reports should name
the epic, the failing file (when applicable), and the specific defect.
Failure messages are grouped by format below — only the messages for the
format selected in step 0 ("Format detection") are emitted for a given epic.

### Format A failures

#### Sprint-status failures

- **`sprint-status.yaml` missing** — Report:
  `Epic K: sprint-status.yaml not found at expected path.`
- **`development_status` map missing or malformed** — Report:
  `Epic K: sprint-status.yaml present but development_status map is missing or not a mapping.`
- **Story-1 key not found** — Report:
  `Epic K: no entry matching {K}-1-* in development_status.`
- **Story-1 status is not `done`** — Report:
  `Epic K: story {key} status is {value}, expected done.`

#### Micro-PRD failures

- **File missing** — Report:
  `Epic K: epic-K-micro-prd.md not found in _bmad-output/implementation-artifacts/.`
- **Required section header missing** — Report (one line per missing header):
  `Epic K: epic-K-micro-prd.md missing required section "## {name}".`
- **Required section present but empty** — Report:
  `Epic K: epic-K-micro-prd.md section "## {name}" is empty.`

#### Micro-architecture failures

- **File missing** — Report:
  `Epic K: epic-K-micro-architecture.md not found in _bmad-output/implementation-artifacts/.`
- **Required section header missing** — Report (one line per missing header):
  `Epic K: epic-K-micro-architecture.md missing required section "## {name}".`
- **Required section present but empty** — Report:
  `Epic K: epic-K-micro-architecture.md section "## {name}" is empty.`

### Format A-equivalent failures

#### Sprint-status failures (A-equivalent)

Identical to Format A sprint-status failures above.

#### Whole-project architecture failures

- **File missing** — Report:
  `Epic K: whole-project architecture.md not found at _bmad-output/planning-artifacts/architecture.md.`
- **Frontmatter missing or malformed** — Report:
  `Epic K: architecture.md has no parseable YAML frontmatter block.`
- **`status` frontmatter missing or not `complete`** — Report:
  `Epic K: architecture.md frontmatter status is {value}, expected complete.`
- **`stepsCompleted` frontmatter incomplete** — Report:
  `Epic K: architecture.md frontmatter stepsCompleted is {value}, expected all of [1,2,3,4,5,6,7,8].`

#### Whole-project SPEC / PRD failures

- **Neither SPEC nor PRD found** — Report:
  `Epic K: no SPEC.md under _bmad-output/specs/spec-*/ and no prd.md under _bmad-output/planning-artifacts/prds/*/.`

### Reporting policy

- Collect **all** failures for an epic before reporting; do not short-circuit
  on the first failure. The operator should see the full picture for the
  epic in one pass.
- When at least one failure exists for an epic, that epic is **not**
  tracer-ready and must not be fanned out.
- When all checks for the selected format pass (all three Format A checks,
  or all three Format A-equivalent checks), the epic proceeds to the
  inspection-halt presentation below for operator confirmation.

## Inspection-halt presentation format

When all automated checks pass, the skill pauses for human confirmation
before treating the epic as a real, fan-out-ready tracer. Automated checks
verify the *shape* of the contract; the operator verifies the *substance*
(i.e., "is this actually a tracer, or just a file that satisfies the
headers?").

For each tracer-ready epic, present the following block verbatim, filling in
the bracketed values:

```
Epic K — tracer-readiness check:
  Format used: A | A-equivalent
  Story K.1: <key>  (status: done|<other>)
  Files touched (git diff K.1, if available):
    <path> +<adds> -<dels>
  Tracer docs:
    epic-K-micro-prd.md            (<size> bytes; <line-1>)
    epic-K-micro-architecture.md   (<size> bytes; <line-1>)
  
  Does this look like a real tracer? [y/N]
```

Under Format A-equivalent, the `Tracer docs:` block shows the whole-project
artifacts instead of the per-epic micro-docs:

```text
  Tracer docs (whole-project; single-epic short-circuit):
    architecture.md   (<size> bytes; <line-1>)
    SPEC.md (or prd.md)   (<size> bytes; <line-1>)
```

The `Format used:` line is always present and renders the literal label
(`A` or `A-equivalent`) of the format selected in step 0.

### Field semantics

- `K` — the epic number.
- `<key>` — the story-1 key from `sprint-status.yaml` (e.g.
  `1-1-data-model`).
- `status` — the literal value from `development_status[<key>]`. In the
  inspection-halt path this will always be `done`; the `|<other>` alternative
  is shown for completeness because the same template may also be used by
  diagnostics.
- `Files touched (git diff K.1, if available)` — the list of files modified
  by the tracer commit(s), one per line, formatted as
  `<path> +<adds> -<dels>`. If git diff data is not available (e.g. the repo
  is not initialized, the story commit cannot be identified, or git is not
  on PATH), render the literal line `(git diff unavailable)` in place of the
  per-file list. Do not omit the section header.
- `<size>` — file size in bytes for each tracer doc.
- `<line-1>` — the first non-empty line of the tracer doc (typically its
  `# Title` header), truncated to a reasonable single-line length (e.g. 80
  characters) if needed.
- `Does this look like a real tracer? [y/N]` — the prompt. The default is
  `N`; only an explicit affirmative ("y", "yes") advances. Anything else,
  including empty input, halts fan-out for that epic.

### Multi-epic runs

When several epics pass automated checks in the same invocation, present one
block per epic, separated by a blank line, and prompt for each independently.
Do not batch the confirmations into a single yes/no — each epic earns its
own decision.
