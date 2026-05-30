export const meta = {
  name: 'phase1e-scan',
  description: 'bmad-auto Stage 1.e scan+collate: parallel execute-access unknowns-hunter + edge-case-hunter, schema-validated findings, deterministic JS collate, persist epic-K-phase1-findings.json from inside the workflow. Hands back to interactive triage. Verify is opt-in (factual-only, FAIL-gated, annotate-only).',
  whenToUse: 'Invoked by bmad-auto Stage 1.e Step 1-2 to produce the scan+collate findings file for an epic before operator triage.',
  phases: [
    { title: 'Scan', detail: 'parallel unknowns-hunter + edge-case-hunter, execute-access, schema-validated' },
    { title: 'Verify', detail: 'OPT-IN only: factual-only skeptic per FAIL finding; annotate, never drop' },
    { title: 'Persist', detail: 'writer agent persists the JS-collated findings JSON verbatim' },
  ],
}

// ─────────────────────────────────────────────────────────────────────────────
// args (passed by the bmad-auto skill when it invokes this workflow):
//   epic_id            string   e.g. "100"            (required)
//   story_paths        string[] absolute story paths  (required)
//   architecture_path  string   absolute arch path    (optional)
//   epics_path         string   absolute epics.md     (optional, unknowns context)
//   impl_paths         string[] absolute code paths to ground the scan (optional)
//   repo_root          string   for running the CLI / grep (optional; default cwd)
//   out_path           string   absolute path for epic-K-phase1-findings.json (required)
//   now                string   UTC ISO-8601 stamp (optional; writer stamps if absent)
//   verify             boolean  opt-in factual-only FAIL-gated verify (default false)
// The JS sandbox has NO filesystem access and cannot call new Date(), so the file
// is written by a dedicated writer agent (persist phase), never by the JS and never
// hand-transcribed by the orchestrator — that lossy path is exactly what the spike
// caught (see docs/phase1e-workflow-decision.md).
// ─────────────────────────────────────────────────────────────────────────────

// args may arrive as a parsed object or a JSON string depending on the caller — normalize.
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (_e) { /* leave as-is */ } }
A = (A && typeof A === 'object') ? A : {}
const EPIC = String(A.epic_id != null ? A.epic_id : '')
const STORY_PATHS = Array.isArray(A.story_paths) ? A.story_paths : []
const IMPL_PATHS = Array.isArray(A.impl_paths) ? A.impl_paths : []
const ARCH = A.architecture_path || null
const EPICS = A.epics_path || null
const REPO_ROOT = A.repo_root || null
const OUT_PATH = A.out_path || null
const NOW = A.now || '__COLLATED_AT__' // writer substitutes the literal if no stamp supplied
const DO_VERIFY = A.verify === true

if (!EPIC) throw new Error('phase1e-scan: args.epic_id is required')
if (!STORY_PATHS.length) throw new Error('phase1e-scan: args.story_paths[] is required')
if (!OUT_PATH) throw new Error('phase1e-scan: args.out_path is required')

const bullets = (arr) => arr.map((p) => `  - ${p}`).join('\n')
const archLine = ARCH ? `\n- architecture: ${ARCH}` : ''
const epicsLine = EPICS ? `\n- epic context: ${EPICS} (read the "## Epic ${EPIC}" section + capability rows)` : ''
const implBlock = IMPL_PATHS.length
  ? `\n- implementation under test (ground the scan in real code; RUN it):\n${bullets(IMPL_PATHS)}`
  : ''
const runHint = REPO_ROOT ? ` from ${REPO_ROOT}` : ''

// ── Per-hunter findings schema = the Stage 1.e scan contract. Each hunter is
//    FORCED to return this shape via StructuredOutput; the model retries on mismatch.
const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['epic_id', 'scan_at', 'findings'],
  properties: {
    epic_id: { type: 'string' },
    scan_at: { type: 'string', description: 'UTC ISO 8601 at scan completion (run `date -u +%Y-%m-%dT%H:%M:%SZ`)' },
    scan_notes: { type: 'string', description: 'optional one-paragraph coverage summary; required when findings is empty so triage knows the scan ran' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'source', 'category', 'severity', 'story_id', 'description', 'cross_layer_flags'],
        properties: {
          id: { type: 'string' },
          source: { type: 'string', enum: ['unknowns', 'edge-case'] },
          category: { type: 'string' },
          severity: { type: 'string', enum: ['FAIL', 'CONCERNS', 'INFO'] },
          story_id: { type: ['string', 'null'] },
          description: { type: 'string' },
          cross_layer_flags: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

const UNKNOWNS_PROMPT = `You are the **Unknowns-hunter** — a focused, read-only adversarial scanner for the bmad-auto Phase 1.e hardening stage. Walk the upstream artifacts for epic ${EPIC} and surface every external unknown that could block or destabilize Phase 2 launch. Do NOT write files, do NOT edit anything, do NOT invoke other skills. Return ONLY the structured findings object.

## YOU HAVE EXECUTE ACCESS — USE IT
You have Bash/read access. Ground every finding in reality: RUN the real artifacts (e.g. \`python3 <cli> <subcmd>\`${runHint}), grep the CI dir (\`.github/\`) for coverage gaps, read any file you need. A blind read-only scan misses the most valuable unknowns — running the code is the single biggest quality lever (spike finding). Probing is read-only; just do not modify anything.

## Epic under scan
epic_id "${EPIC}".

## Inputs (read in full, read-only)${archLine}${epicsLine}
- stories:
${bullets(STORY_PATHS)}${implBlock}
If there is no consolidated Stage 1.d unknowns_report, derive unknowns directly from the artifacts above.

## Method — SPIKES (six categories). Walk each exhaustively; surface every substantiated unknown, not one-per-category. Omit a category with no substantiated unknown (no INFO placeholder filler).
1. Scope — epic boundary fully delineated, no ambiguity vs adjacent epics? scope-creep, straddling stories, capabilities with no story.
2. Packages — all third-party packages identified, pinned where it matters, installable now?
3. Integrations — external integration points known well enough to wire the tracer? auth, contracts, rate limits, sandbox-vs-prod.
4. Knowledge — domain model / behavior clear enough that ACs are unambiguous? unresolved domain questions, undocumented invariants.
5. Environment — dev/CI/test env ready? missing CI jobs, unauthored fixtures, unprovisioned config, local setup gaps.
6. Surface — CLI/API surface specific enough to generate testable stories? contract ambiguities.

## Severity: FAIL = blocks Phase 2 entry; CONCERNS = needs operator decision, no auto-block; INFO = nice-to-know. Between adjacent levels, choose the higher.

## Output: emit the structured findings object.
- epic_id "${EPIC}"; scan_at = output of \`date -u +%Y-%m-%dT%H:%M:%SZ\`.
- id pattern "unknowns-<n>" (from 1); source always "unknowns".
- category one of Scope|Packages|Integrations|Knowledge|Environment|Surface.
- story_id = the K-N id for a story-scoped unknown, or null for an epic-scope one.
- description = one paragraph, descriptive only (no resolutions). cross_layer_flags always [] (the collate step fills it).
- scan_notes = a one-paragraph coverage summary. If there are genuinely no substantiated unknowns, return an empty findings array AND a scan_notes explaining why (a legitimate result for a tightly-scoped epic).`

const EDGE_PROMPT = `You are the **Edge-case-hunter** — a focused, read-only adversarial scanner for the bmad-auto Phase 1.e hardening stage. Apply the bmad-review-edge-case-hunter method across every story file for epic ${EPIC} and surface every unhandled boundary, branch, or edge an autonomous Phase 3 implementation would stumble on. Do NOT write files, do NOT edit stories. Return ONLY the structured findings object.

## YOU HAVE EXECUTE ACCESS — USE IT
You have Bash/read access. Ground the edge analysis in real code: read the implementation, and RUN it${runHint} to confirm a trigger actually fires before reporting it. Probing is read-only; do not modify anything.

## Epic under scan
epic_id "${EPIC}".

## Inputs (read in full, read-only)${archLine ? `\n- architecture (use as also_consider for cross-architecture coupling): ${ARCH}` : ''}
- stories (frontmatter + ACs + Dev Notes for each):
${bullets(STORY_PATHS)}${implBlock}

## Method (edge-case-hunter, per story)
Read each story in full. Treat ACs verbatim + Dev Notes verbatim + embedded contracts as review content; weigh the architecture as cross-coupling. Path-trace for unhandled edges, producing {location, trigger_condition, guard_snippet, potential_consequence}-style findings and MAP each into the output schema (one edge -> one row). Trace exhaustively per story; do not cap N. If a story has zero unhandled edges, emit no rows for it (no INFO placeholders).

## Field mapping -> output
- id: "edge-case-<n>" (running index across all stories, from 1).
- source: always "edge-case".
- category: derived from the trigger — one of branch (missing else/default/early-return), boundary (off-by-one, null/empty, coercion), concurrency (race/timeout/retry), state (invariant violation, ordering), input (unguarded input, validation gap), error-handling (uncaught/swallowed/propagation gap). Pick closest; do not invent.
- severity: FAIL if consequence is data loss / auth bypass / security / unrecoverable state; CONCERNS if functional incorrectness the user would notice; INFO if cosmetic/theoretical. When in doubt choose higher.
- story_id: the K-N id from frontmatter; null only for epic-scope findings spanning stories.
- description: one paragraph combining trigger_condition + location + potential_consequence into triageable prose.
- cross_layer_flags: always [] (the collate step fills it).

## Output: emit the structured findings object (epic_id "${EPIC}", scan_at = output of \`date -u +%Y-%m-%dT%H:%M:%SZ\`, findings[]). Optionally set scan_notes to a one-line coverage summary. Faithful, non-editorialized mapping; exhaustive within scope.`

// ── Scan: two hunters in parallel, each schema-validated, each execute-access ──
phase('Scan')

const [unknowns, edge] = await parallel([
  () => agent(UNKNOWNS_PROMPT, { label: 'unknowns-hunter', phase: 'Scan', schema: FINDINGS_SCHEMA }),
  () => agent(EDGE_PROMPT, { label: 'edge-case-hunter', phase: 'Scan', schema: FINDINGS_SCHEMA }),
])

const u = unknowns || {}
const e = edge || {}
const uFindings = Array.isArray(u.findings) ? u.findings : []
const eFindings = Array.isArray(e.findings) ? e.findings : []

// ── Collate (deterministic JS, off the main context) ─────────────────────────
// Conservative dedupe + cross-link. We never silently delete a non-duplicate
// finding — only collapse byte-identical descriptions and annotate the rest.
const norm = (s) => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim()

// 1. Merge (unknowns first, then edge-case), dropping only exact-duplicate descriptions.
const merged = []
const seen = new Map() // normalized description -> survivor finding
for (const f of [...uFindings, ...eFindings]) {
  const key = norm(f.description)
  if (seen.has(key)) {
    const survivor = seen.get(key)
    if (!survivor.cross_layer_flags.includes(f.id)) survivor.cross_layer_flags.push(f.id)
    continue
  }
  const copy = { ...f, cross_layer_flags: Array.isArray(f.cross_layer_flags) ? [...f.cross_layer_flags] : [] }
  seen.set(key, copy)
  merged.push(copy)
}

// 2. Cross-link findings that share a high-signal MECHANISM token (whole-word, not
//    substring) or a cli.py:NN-style code reference. Curated + biased to under-link;
//    whole-word matching avoids noise from short substrings (e.g. "ci" inside
//    "specific"). Links are mutual and apply across both same- and cross-source
//    pairs (the real epic-K artifact links within edge-case too, e.g. ec-3 -> ec-2).
const SIGNAL_TOKENS = new Set([
  'symlink', 'newline', 'permissionerror', 'brokenpipe', 'toctou', 'is_dir',
  'iterdir', 'resolve', 'readme', 'excluded_names', 'filenotfounderror',
])
const codeRefs = (s) => new Set((String(s).match(/[a-z0-9_/-]+\.py:\d+(?:-\d+)?/gi) || []).map((x) => x.toLowerCase()))
const wordsOf = (s) => new Set(norm(s).split(/[^a-z0-9_]+/).filter(Boolean))
const tokensOf = (f) => {
  const words = wordsOf(f.description)
  const set = new Set()
  for (const t of SIGNAL_TOKENS) if (words.has(t)) set.add(t)
  for (const r of codeRefs(f.description)) set.add(r)
  return set
}
const tokIndex = merged.map((f) => ({ f, toks: tokensOf(f) }))
for (let i = 0; i < tokIndex.length; i++) {
  for (let j = i + 1; j < tokIndex.length; j++) {
    const a = tokIndex[i]
    const b = tokIndex[j]
    let shared = false
    for (const t of a.toks) {
      if (b.toks.has(t)) { shared = true; break }
    }
    if (!shared) continue
    if (!a.f.cross_layer_flags.includes(b.f.id)) a.f.cross_layer_flags.push(b.f.id)
    if (!b.f.cross_layer_flags.includes(a.f.id)) b.f.cross_layer_flags.push(a.f.id)
  }
}
for (const f of merged) f.cross_layer_flags.sort()

const findings = merged
const countSev = (s) => findings.filter((f) => f.severity === s).length
const scanAt = u.scan_at || e.scan_at || NOW
const unknownsNotes =
  u.scan_notes ||
  (uFindings.length === 0
    ? `Unknowns (SPIKES) scan across all six categories surfaced no substantiated unknowns for epic ${EPIC}.`
    : '')

const collated = {
  epic_id: u.epic_id || e.epic_id || EPIC,
  scan_at: scanAt,
  collated_at: NOW,
  scan_summary: {
    unknowns_findings: uFindings.length,
    edge_case_findings: eFindings.length,
    fail_count: countSev('FAIL'),
    concerns_count: countSev('CONCERNS'),
    info_count: countSev('INFO'),
    unknowns_notes: unknownsNotes,
  },
  findings,
}

log(
  `Scan+collate: ${uFindings.length} unknowns + ${eFindings.length} edge-case → ${findings.length} findings ` +
    `(FAIL ${countSev('FAIL')} / CONCERNS ${countSev('CONCERNS')} / INFO ${countSev('INFO')}); ` +
    `${findings.reduce((n, f) => n + f.cross_layer_flags.length, 0)} cross-layer links`
)

// ── Verify (OPT-IN ONLY): factual-only, FAIL-gated, annotate-never-drop ───────
// Default path skips this entirely (spike: a default keep/drop verifier destroys
// triageable signal). When enabled it only flags FAIL findings whose trigger does
// not factually occur; it NEVER removes a finding — triage stays the operator's job.
let verify_summary = null
if (DO_VERIFY) {
  phase('Verify')
  const failFindings = findings.filter((f) => f.severity === 'FAIL')
  if (failFindings.length === 0) {
    verify_summary = { ran: true, scope: 'FAIL-only', checked: 0, note: 'no FAIL findings to verify' }
    log('Verify (opt-in): no FAIL findings; nothing to check.')
  } else {
    const VERDICT_SCHEMA = {
      type: 'object',
      additionalProperties: false,
      required: ['finding_id', 'factually_substantiated', 'confidence', 'reason'],
      properties: {
        finding_id: { type: 'string' },
        factually_substantiated: { type: 'boolean' },
        confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        reason: { type: 'string' },
      },
    }
    const verifyPrompt = (f) => `You are a FACTUAL-SUBSTANTIATION verifier for a bmad-auto Phase 1.e FAIL finding on epic ${EPIC}. Decide ONLY whether the finding is factually grounded in the actual code/artifacts.

Set factually_substantiated=false ONLY if the finding is factually WRONG: the described trigger does NOT actually occur when you check, the code is misdescribed (wrong line/behavior/flow), or a cited artifact state does not exist.
DO NOT mark it false on grounds of scope, theory ("won't happen for this CLI"), severity, or "the operator should decide" — those are triage judgments, not factual refutations. Default to true when uncertain. This verdict only FLAGS the finding; it never removes it.

You MAY read/run the artifacts${runHint} to confirm:
${IMPL_PATHS.length ? bullets(IMPL_PATHS) + '\n' : ''}${bullets(STORY_PATHS)}

## FINDING (severity ${f.severity})
- finding_id: ${f.id}
- source/category: ${f.source} / ${f.category}
- story_id: ${f.story_id === null ? 'null (epic-scope)' : f.story_id}
- description: ${f.description}

## Output: emit the verdict object. finding_id MUST be exactly "${f.id}".`

    const verdicts = await parallel(
      failFindings.map((f) => () =>
        agent(verifyPrompt(f), { label: `verify:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      )
    )
    const byId = {}
    verdicts.filter(Boolean).forEach((v) => { byId[v.finding_id] = v })
    // Annotate ONLY — attach a verify flag; do not drop anything.
    for (const f of findings) {
      if (f.severity === 'FAIL' && byId[f.id]) f.verify = byId[f.id]
    }
    const unsubstantiated = failFindings.filter((f) => byId[f.id] && byId[f.id].factually_substantiated === false)
    verify_summary = {
      ran: true,
      scope: 'FAIL-only',
      calibration: 'factual-only (flag, never drop)',
      checked: failFindings.length,
      verdicts_returned: verdicts.filter(Boolean).length,
      flagged_unsubstantiated: unsubstantiated.map((f) => `${f.id}: ${byId[f.id].reason}`),
    }
    log(`Verify (opt-in): checked ${failFindings.length} FAIL findings, flagged ${unsubstantiated.length} as unsubstantiated (none removed).`)
  }
}

// ── Persist (writer agent — JS has no fs; orchestrator must NOT hand-transcribe) ─
phase('Persist')

const PAYLOAD = JSON.stringify(collated, null, 2)
const persistPrompt = `You are a file WRITER. Persist the Stage 1.e findings artifact for epic ${EPIC}.

## TASK
1. Write the EXACT content in the CONTENT block below to this absolute path, using the Write tool:
   ${OUT_PATH}
2. Write it BYTE-FOR-BYTE. Do NOT reformat, re-indent, summarize, reorder keys, drop fields, or "fix" anything.
   The ONLY permitted change: if you see the literal token __COLLATED_AT__ anywhere, replace EACH occurrence with the current UTC timestamp from \`date -u +%Y-%m-%dT%H:%M:%SZ\` (an ISO-8601 string like 2026-05-28T20:00:00Z). If __COLLATED_AT__ does not appear, change nothing at all.
3. After writing, validate and report:
   - run \`python3 -m json.tool ${OUT_PATH} > /dev/null && echo VALID || echo INVALID\`
   - run \`python3 -c "import json;d=json.load(open('${OUT_PATH}'));print(len(d['findings']))"\` to count findings.

## CONTENT (write this verbatim, modulo the __COLLATED_AT__ rule):
${PAYLOAD}

## Output: emit ONLY this JSON object:
{ "written_path": "${OUT_PATH}", "json_valid": true|false, "findings_written": <int> }`

const PERSIST_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['written_path', 'json_valid', 'findings_written'],
  properties: {
    written_path: { type: 'string' },
    json_valid: { type: 'boolean' },
    findings_written: { type: 'integer' },
  },
}

const persist = await agent(persistPrompt, { label: 'persist-findings', phase: 'Persist', schema: PERSIST_SCHEMA })

const ok = !!persist && persist.json_valid === true && persist.findings_written === findings.length
log(
  `Persist: wrote ${persist ? persist.findings_written : '?'}/${findings.length} findings to ${OUT_PATH} ` +
    `(json_valid=${persist ? persist.json_valid : '?'}, match=${ok})`
)

return {
  epic_id: collated.epic_id,
  out_path: OUT_PATH,
  scan_summary: collated.scan_summary,
  persisted: persist || null,
  persist_matches_collate: ok,
  verify_summary,
  collated, // canonical object so the caller can diff the written file as a final guard
}
