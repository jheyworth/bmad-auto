# bmad-auto

`/bmad-auto` is a **per-epic execution conductor** for the
[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) toolchain. It drives a
hardened epic through four phases, concentrating human-in-the-loop (HITL) at the
start and end and running the middle autonomously:

1. **Phase 1 — Per-epic hardening** (heavy HITL): validate upstream artifacts,
   extract residual unknowns, run a parallel unknowns + edge-case scan, unified
   operator triage.
2. **Phase 2 — Tracer-bullet** (heavy HITL): ATDD red scaffolds + `bmad-quick-dev`
   on story K-1 to resolve unknowns for the rest of the epic.
3. **Phase 3 — Autonomous fanout**: per non-tracer story, a fresh tmux-hosted
   Claude session runs ATDD → quick-dev → coverage → code-review, monitored by a
   stdlib-only Python helper.
4. **Phase 4 — End HITL**: quality gates (trace + NFR) → adversarial review →
   digest → retrospective.

Modes: **Express** (default), **Headless**, **Guided** (`--prep`/`--verify`/`--dev`).

```text
/bmad-auto --epics <K>
```

> **Status: early iteration.** Exercised end-to-end on a small validation epic
> (epics 99–100); not yet battle-tested on production-scale work. Feedback welcome.

## What it adds vs what it reuses

The autonomous middle isn't new — **Phase 3 *is*
[`bmad-story-automator`](https://github.com/bmad-code-org/bmad-automator)'s per-story
loop** (create → dev → review; sequential; tmux-isolated; Codex-capable). What
`/bmad-auto` adds is the **epic-level envelope** that story-level automation
structurally can't:

- **Phase 1** — upfront epic hardening (parallel SPIKES + edge-case scan → operator triage), *before any code*.
- **Phase 2** — the tracer-bullet that locks the epic's architecture/spec contract.
- **Phase 4** — end-of-epic quality gates (traceability + NFR + epic-wide Codex + deferred-delta + digest → retrospective).

It hardens the epic first and gates it after — an envelope around the per-story
loop, not a replacement.

## This is a conductor — it is not runtime-standalone

bmad-auto orchestrates *other* skills and reads the consuming project's
artifacts. Installing this folder alone is necessary but not sufficient to run an
epic; Stage 0 preflight will HALT with a clear message until the toolchain and
inputs below are present. That's by design.

### Runtime prerequisites

**Binaries**
- `tmux`, `python3 >= 3.11`, the `claude` CLI (for per-story sessions)
- optional: `codex` (adversarial review), `git` (full diff fidelity; degrades gracefully without it)

**Sibling skills** (install alongside, e.g. `npx bmad-method@next install --modules bmm,tea --tools claude-code`)
- TEA module: `bmad-testarch-atdd`, `bmad-testarch-trace`, `bmad-testarch-nfr` (preflight-gated)
- `bmad-quick-dev`, `bmad-code-review`, `bmad-retrospective` (Express)
- producers (or pre-author the artifacts yourself): `bmad-sprint-planning`, `bmad-create-story`, `bmad-spec`/`bmad-prd`, `bmad-create-architecture`, `bmad-ux`

**Upstream artifacts** under the consuming project's `_bmad-output/`
- `planning-artifacts/epics.md` (required), `SPEC.md` or `prd.md`, `architecture.md` (status complete)
- `implementation-artifacts/sprint-status.yaml` + per-story files (incl. tracer K-1)
- UX docs only when the SPEC declares a UX surface

## Install

Drop this folder at `.claude/skills/bmad-auto/`, install the sibling skills above,
ensure a prepared `_bmad-output/`, then invoke `/bmad-auto --epics <K>`.

## Phase reference

| Phase | HITL | What it does | Gate / output |
| --- | --- | --- | --- |
| **0 · Preflight** | — | Probe `tmux` / `python3.11+` / TEA / `codex`; confirm epic + inputs exist | HALT if toolchain or inputs missing |
| **1 · Hardening** | heavy | Parallel unknowns (SPIKES) + edge-case scan → unified operator triage | findings JSON; a `FAIL` blocks Phase 2 |
| **2 · Tracer-bullet** | heavy | ATDD red scaffolds + `bmad-quick-dev` on story K-1 | tracer-readiness gate |
| **3 · Fanout** | autonomous | Per story (sequential, tmux): ATDD → quick-dev → coverage → code-review | `sprint-status.yaml` flip per story |
| **4 · End** | heavy | Traceability + NFR gates · epic-wide Codex · deferred-delta · digest · retrospective → correct-course | digest + retrospective |

## Layout

| Path | Contents |
| --- | --- |
| `SKILL.md` | The orchestrator contract (the skill itself) |
| `references/` | Method specs: autonomous-mode directives, tracer-readiness, deferred classifier, hunter prompts, forward-compat trackers |
| `scripts/bmad-auto-helper.py` | stdlib-only tmux spawn/monitor/cadence helper |
| `scripts/tests/` | pytest suite (hermetic unit tests + opt-in live `e2e_*`) |
| `workflows/phase1e-scan.workflow.js` | Phase 1.e parallel hardening scan |
| `assets/` | Templates (tracer story) |
| `test-fixtures/` | Test fixtures (self-contained) |
| `docs/` | Design intent, architecture non-negotiables, decision records |

## Tests

```sh
cd scripts/tests
python3 -m pytest -m "not e2e and not e2e_slow and not e2e_fast"   # hermetic, fast
```

The `e2e_*` tests drive a real `claude` session and need the full toolchain + API
access; they skip when prerequisites are absent.

## Design & rationale

See [`docs/`](docs/) — `bmad-auto-design-intent.md` (authoritative design),
`auto-skills-design.md` (compaction-resilience non-negotiables), and the decision
records (Agent Teams deferral, Epic SPEC bundle forward-compat).

## License & credits

MIT (see [`LICENSE`](LICENSE)). The tmux runtime follows the pattern of
`bmad-story-automator`'s `tmux_runtime.py` (MIT). Built for the BMAD-METHOD
toolchain; implements Alex Verkhovsky's per-epic tracer-bullet pipeline.
