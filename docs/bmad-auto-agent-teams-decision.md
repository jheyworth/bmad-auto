# Decision: defer Agent Teams adoption for `bmad-auto`

**Date:** 2026-05-30
**Status:** Decided — leave as-is, revisit on triggers below.
**Scope:** `skills/bmad-auto` Phase 3 orchestration (and Phase 4 parallel work).

## Decision

Keep `bmad-auto`'s current orchestration as-is — tmux + `skills/bmad-auto/scripts/bmad-auto-helper.py`
spawn/monitor. Do **not** adopt Claude Code Agent Teams yet, and do **not** build a
speculative backend-abstraction seam now. Revisit when the triggers below land.

## Why

- **Plain `/agents` subagents are disqualified for the core.** A subagent cannot fan out
  into skills that themselves spawn workers (Phase 3's `bmad-code-review` parallel layers;
  Phase 4 party-mode retrospective), and cannot be attached/driven by the operator on
  stall/HALT (Stage 3.C.3/3.C.4 Nudge/Drive). The flat-hierarchy rule (no nested subagents)
  is a hard wall.
- **Agent Teams *removes* both blockers.** Teammates are full, independent Claude Code
  sessions: they load project skills/MCP like a normal session (so they can run
  `bmad-quick-dev`, `bmad-testarch-atdd`, `bmad-code-review`'s fan-out, Workflow/Agent
  fan-outs), and the operator can message/steer any teammate directly. So Teams is a
  credible *future* backend for the brittle Phase 3 tmux spawn/monitor layer — it would
  retire the spawn-warmup contract, the two-message split, and the capture-pane grep
  heuristics, replacing them with `TeamCreate` + shared task list + `TeammateIdle` /
  `TaskCompleted` hooks.
- **But Agent Teams currently breaks session resumption** — the property `bmad-auto` exists
  to protect. `/resume` and `/rewind` do not restore in-flight teammates, and the lead is
  fixed for its lifetime. That collides head-on with mid-epic compaction/death resilience +
  resume-from-sprint-status. Migrating Phase 3 now would trade the hardest-won property for
  cleaner spawn code.
- **It's experimental.** Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, Claude Code
  v2.1.32+, shipped Feb 2026 with Opus 4.6. `TeamCreate` / hooks / task-list semantics will
  likely shift before GA, so anything built against today's surface risks rework.
- **Waiting accrues no debt.** `bmad-auto` state already lives in sidecars + sprint-status
  (not transcripts), so later adoption is a *backend swap*, not a redesign.

## Revisit triggers (any one)

1. Agent Teams session resumption restores in-flight teammates — **primary signal**.
2. Agent Teams exits experimental (no env-var gate).
3. `TaskCompleted` / `TeammateIdle` hooks stabilize — enables deterministic sprint-status
   gating instead of capture-pane grep.

## When revisiting

- Pilot lowest-risk first: **Phase 4 parallel review / retrospective** (short-lived,
  conflict-free, no resume dependency) before the **Phase 3 per-story** prize.
- Keep state file-based + sprint-status-authoritative so backends stay interchangeable
  (introduce a `tmux-helper` vs `agent-teams` backend seam, gated on capability detection
  in Stage 0 preflight).
- Mind the tension: Teams is parallel-first; `bmad-auto` is deliberately *sequential within
  an epic* (Alex's pipeline). Serializing would require task-list dependencies (K-3 depends
  on K-2) and conflict-avoidance — overhead that partly offsets the gain.
- Agent Teams uses interactive sessions, **not `claude -p`**, so it stays clean against the
  project's `claude -p` ban (see `CLAUDE.md`).

## Related upstream-watch item: `bmad-quick-dev` headless mode

Tracked here so both upstream dependencies live together.

**Current status (as documented + installed, 2026-05-30):**
- Upstream roadmap (BMadCode, Discord, 2026-05-24):
  *"all of the skills are getting much leaner… all workflows will support headless
  mode, express mode, and full guided modes."* Pipeline also in flux (PRD → `bmad-spec`,
  architecture → architecture-spine).
- Installed `bmad-quick-dev` is a churning **"New Preview Workflow"**, checkpoint/HITL by
  default — **no native headless/express/autonomous mode yet**.
- Consequence: `bmad-auto` forces autonomous behavior by pasting
  `references/autonomous-mode-directives.md` (8 directives, ~5KB) verbatim into every
  per-story spawn — which is also what forces the two-message split (the ~5KB payload
  exceeds Claude Code's 4000-char `/goal` ceiling).

**Why we wait / stay permissive:**
- Design intent Q1c keeps `bmad-auto` *out of* quick-dev's `intent_gap` machinery
  (quick-dev is the authoritative handler), precisely so quick-dev can evolve without
  forcing a `bmad-auto` redesign.

**Revisit trigger:** when `bmad-quick-dev` ships a native headless/express mode, retire
most of the directive-injection scaffolding (replace the verbatim 8-directive paste +
two-message split with a flag). This is a *simplification*, not a redesign — same posture
as the Agent Teams item above.

## Sources

- Reference: `sub-agents-chat-session.md` (subagents vs skills, fact-checked 2026-05-30).
- Claude Code docs: `code.claude.com/docs/en/agent-teams`, `code.claude.com/docs/en/sub-agents`.
- Analysis: this session (2026-05-30).
- Related: `docs/auto-skills-design.md` (compaction-resilience non-negotiables),
  `docs/phase1e-workflow-decision.md` (existing Workflow-based fan-out precedent).
