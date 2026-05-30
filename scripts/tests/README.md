# bmad-auto pytest suite

Two distinct test groups live in this directory:

1. **Helper unit tests** (`test_derive_cadence.py`, `test_halt_check_*.py`,
   `test_monitor_*.py`, `test_spawn_*.py`) — cover all five subcommands
   of `bmad-auto-helper.py` (`spawn`, `monitor`, `halt-check`,
   `derive-cadence`, `kill`). Fast, hermetic, run by default.
2. **End-to-end tests** (`test_e2e_*.py`) — drive a real `claude`
   session inside tmux against the committed fixture at
   `../../test-fixtures/e2e/happy/`. Slow, opt-in via
   `-m e2e_fast` or `-m e2e_slow`. See "E2E suite" section below.

## Running

From the repo root:

```sh
python3 -m pytest skills/bmad-auto/scripts/tests/ -v
```

To run a single file:

```sh
python3 -m pytest skills/bmad-auto/scripts/tests/test_halt_check_grep.py -v
```

## Prerequisites

- `python3 >= 3.11` (stdlib-only suite — no `requirements.txt`).
- `pytest` (test-time dependency only). Install with:

  ```sh
  python3 -m pip install --user pytest
  ```

- `tmux` is optional. The single integration test
  (`test_spawn_kill_smoke.py`) is skipped automatically when `tmux` is
  not on `PATH`.

## Test files

| File | Subcommand(s) | Approach |
| --- | --- | --- |
| `test_derive_cadence.py` | `derive-cadence` | Subprocess (CLI contract). |
| `test_halt_check_sidecar.py` | `halt-check` (sidecar primary path) | Library call (`check_halt`). |
| `test_halt_check_grep.py` | `halt-check` (capture-pane grep fallback) | Library call with patched `run_tmux`. |
| `test_monitor_happy_path.py` | `monitor` — `completed` outcome | Library call (`cmd_monitor`) + patched I/O. |
| `test_monitor_halted.py` | `monitor` — `halted` outcome | Library call with sidecar fixture staged. |
| `test_monitor_stalled.py` | `monitor` — `stalled` outcome | Library call; identical capture-pane → stall trip. |
| `test_monitor_timeout.py` | `monitor` — `timeout` outcome | Library call; patched `time.time` to advance the clock. |
| `test_spawn_kill_smoke.py` | `kill` | Integration test against real tmux (skipped if absent). |

## Fixtures reused from `../../test-fixtures/halt-detection/`

The HALT-detection fixture suite is the source of truth for both
positive and negative HALT-classifier inputs:

- **Sidecar fixtures** — `sidecar-intent-gap.json`,
  `sidecar-bad-spec.json`, `sidecar-red-tests-failing.json`,
  `negative-sidecar-malformed.json`.
- **Capture-pane fixtures** — `trigger-*.txt` (7 positives) and
  `negative-*.txt` (5 negatives). Test files read these via the
  `fixtures_dir` fixture and pipe them through a patched
  `helper.run_tmux` so the production code path runs unmodified.

The fixture README at `../../test-fixtures/halt-detection/README.md`
documents which "negative" fixtures are clean negatives versus
documented heuristic limitations (false-positives the substring-based
matcher cannot avoid without semantic understanding). Tests in
`test_halt_check_grep.py` assert the current behavior for the
documented-limitation cases with explanatory comments — these are
regression baselines, not aspirational targets.

## Conftest fixtures

Defined in `conftest.py`:

- `helper` — the loaded helper module (filename has a hyphen; we load
  via `importlib.util.spec_from_file_location`). Per-test so monkey-
  patches don't leak.
- `helper_script_path` — absolute Path to the helper script, for
  subprocess invocations.
- `fixtures_dir` — Path to the halt-detection fixture directory.
- `mock_tmux` — MagicMock that replaces `helper.run_tmux`.
- `fast_sleep` — patches `helper.time.sleep` to a no-op (keeps monitor
  tests under 5 seconds total).
- `sprint_status_tmp` — tmp `_bmad-output/implementation-artifacts/`
  directory plus a `{story_id: status}` writer.

## Why two test approaches

- **Library calls (Option A)** dominate the suite. They unit-test the
  pure functions (`check_halt`, `cmd_monitor` with patched I/O,
  `_apply_tail_window`, etc.) without subprocess overhead and give
  precise control over `run_tmux` / `read_sprint_status` / `time.sleep`.
- **Subprocess calls (Option B)** are used where the CLI contract
  itself is the thing under test: `derive-cadence` emits a bare integer
  to stdout (no JSON wrapping), and `kill` integration verifies the
  real-tmux end-to-end path.

## Expected runtime

The full suite runs in well under 5 seconds on a developer laptop.
Monitor tests use a patched `time.sleep` no-op and (for the timeout
test) a synthetic clock so they never block on real wall-clock waits.

---

## E2E suite

The four `test_e2e_*.py` files run the full `/bmad-auto` orchestrator
end-to-end against a fixture epic. They are opt-in (default `addopts`
in `pytest.ini` excludes them) and grouped into fast vs. slow:

| Test | Variant | Mode | Marker | Budget |
| --- | --- | --- | --- | --- |
| `test_e2e_preflight_halt.py` | T3 | preflight HALT | `e2e_fast` | ~60s |
| `test_e2e_phase1_fail.py` | T2 | Phase 1 FAIL HALT | `e2e_fast` | ~10 min |
| `test_e2e_happy_headless.py` | T1 | full headless run | `e2e_slow` | ~90 min |
| `test_e2e_express_consent.py` | T4 | Express + consent + full run | `e2e_slow` | ~90 min |

### Running locally

```sh
# Fast tests (T2 + T3) — usable for per-push regression
cd skills/bmad-auto/scripts/tests
python3 -m pytest -v -m e2e_fast

# Slow tests (T1 + T4) — full e2e, ~$ per run in Claude API
python3 -m pytest -v -m e2e_slow

# Single test (e.g. for debugging)
python3 -m pytest -v test_e2e_preflight_halt.py
```

### Prerequisites for e2e

- `tmux` on PATH
- `claude` CLI on PATH and authenticated
- Python 3.11+
- The automator repo's `.claude/skills/bmad-testarch-*` populated (the
  driver symlinks `.claude/` into the fixture tmpdir; if TEA is missing
  there, preflight will HALT)

### Components

- `e2e_driver.py` — fixture prep, tmux+claude spawning, terminal-state
  polling, teardown
- `e2e_assertions.py` — per-phase assertion functions + composite
  bundles per test variant
- Fixture sources at `../../test-fixtures/e2e/happy/` (T2/T3
  apply small overlays/omissions via conftest fixtures)

### Postmortem

pytest's `tmp_path` is preserved on failure under
the pytest cache dir (or the system temp `pytest-of-<user>` dir). Inspect:

- The fixture tmpdir's `_bmad-output/.run-state/` for partial sidecars
- The driver's pane capture (printed on assertion failure)
- The orchestrator session's `_bmad-output/.run-state/epic-99-story-*-halt-context.txt` for HALT details
