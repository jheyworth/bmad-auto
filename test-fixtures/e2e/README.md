# bmad-auto e2e test fixtures

End-to-end fixtures for the `/bmad-auto` orchestrator. Each variant is a
minimal "epic-in-a-box": all upstream artifacts (brief / SPEC /
architecture / epics.md / sprint-status / per-story files) prebuilt so
the orchestrator has nothing to ask about and can run autonomously.

| Variant | Purpose | Used by |
| --- | --- | --- |
| `happy/` | Two-story epic that completes cleanly end-to-end | T1 (headless happy-path), T4 (Express consent gate) |
| `phase1-fail/` | Same as `happy/` but with a planted `[CRITICAL]` finding that the Phase 1 unknowns-hunter must FAIL on | T2 (headless FAIL HALT) |
| `preflight-halt/` | Fixture missing `epics.md` to exercise the preflight HALT path | T3 (preflight HALT) |

## Fixture conventions

- **Epic number is `99`** across all variants — picked to never collide
  with real-project epics.
- **Two stories per epic**: `99-1-tracer` and `99-2-fanout`. Single epic
  per fixture exercises the **Format A-equivalent** tracer-readiness path
  (per SKILL.md:586), which is the realistic default for single-epic
  projects under unmodified BMAD toolchains.
- **`ux_surface: none`** in every SPEC bypasses the DESIGN/EXPERIENCE
  gate (per SKILL.md Stage 1.a conditional row).
- **Trivial ACs** — each story writes a single file with a known
  content. Lets `bmad-quick-dev` close in seconds while still producing
  a real diff that exercises the Phase 4 Codex / quality-gate path.

## How fixtures are consumed

The e2e driver at `skills/bmad-auto/scripts/tests/e2e_driver.py`:

1. Copies the variant's tree to a tmpdir
2. `git init`s the tmpdir + initial commit
3. Symlinks `.claude/` and `_bmad/` from the automator repo so the
   orchestrator can resolve sub-skills + TEA config
4. Spawns a tmux-hosted `claude --dangerously-skip-permissions` session
   with cwd set to the tmpdir
5. Pastes the appropriate `/bmad-auto …` invocation via `send-keys`
6. Polls sidecar files for the terminal state
7. Hands the tmpdir path to the assertion library

See `skills/bmad-auto/scripts/tests/README.md` for the full e2e suite
contract.
