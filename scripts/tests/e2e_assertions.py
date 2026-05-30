"""Per-phase assertion library for the bmad-auto e2e tests.

Each assertion function takes a `DriverResult` (from `e2e_driver.py`)
and returns a list of human-readable failure strings — empty list means
all assertions passed. Tests compose these per-variant.

Why functions returning failure lists, not pytest assert calls: it
lets a single test report ALL failures at once (better signal for slow,
expensive e2e runs) and lets the assertions be reused across T1/T2/T3/T4
without duplicating pytest scaffolding.
"""

from __future__ import annotations

import json
import pathlib
from typing import Iterable

from e2e_driver import DriverResult

# Canonical paths (relative to fixture_root)
PATH_PHASE1_FINDINGS = "_bmad-output/.run-state/epic-99-phase1-findings.json"
PATH_ARCH_MODE = "_bmad-output/.run-state/architecture-mode.txt"
PATH_TRACE_GATE = "_bmad-output/.run-state/epic-99-trace-gate.txt"
PATH_NFR_GATE = "_bmad-output/.run-state/epic-99-nfr-gate.txt"
PATH_NFR_DECISION = "_bmad-output/.run-state/epic-99-nfr-decision.json"
PATH_CODEX_SKIPPED = "_bmad-output/.run-state/epic-99-codex-skipped.txt"
PATH_TRACEABILITY = "_bmad-output/implementation-artifacts/epic-99-traceability-matrix.md"
PATH_GATE_DECISION = "_bmad-output/implementation-artifacts/epic-99-gate-decision.json"
PATH_NFR_REPORT = "_bmad-output/implementation-artifacts/epic-99-nfr-assessment.md"
PATH_CODEX_REPORT = "_bmad-output/implementation-artifacts/epic-99-codex-review.md"
PATH_DEFERRED_DELTA = "_bmad-output/implementation-artifacts/epic-99-deferred-delta.md"

# Expected story outputs
EXPECTED_TRACER_CONTENT = "tracer-story-99-1\n"
EXPECTED_FANOUT_CONTENT = "fanout-story-99-2\n"

VALID_TRACE_STATUSES = {"PASS", "CONCERNS", "FAIL", "WAIVED"}
VALID_NFR_STATUSES = {"PASS", "CONCERNS", "FAIL"}


# --- Building blocks ---------------------------------------------------------


def _file_exists(root: pathlib.Path, rel: str) -> bool:
    return (root / rel).is_file()


def _read_json(root: pathlib.Path, rel: str) -> tuple[dict | None, str | None]:
    path = root / rel
    if not path.is_file():
        return None, f"{rel}: file does not exist"
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:
        return None, f"{rel}: invalid JSON ({exc})"


# --- Preflight assertions (used by T3) ---------------------------------------


def assert_preflight_halt(result: DriverResult) -> list[str]:
    """T3: orchestrator HALTed at Stage 0, never reached Phase 1."""
    failures: list[str] = []

    if result.terminal_state != "preflight-halted":
        failures.append(
            f"terminal_state={result.terminal_state}, expected preflight-halted. "
            f"pane tail: {result.pane_capture[-500:]!r}"
        )

    # Stage 3+ sidecars must NOT exist
    for rel in (
        PATH_PHASE1_FINDINGS,
        PATH_TRACEABILITY,
        PATH_GATE_DECISION,
        "_bmad-output/.run-state",
    ):
        full = result.fixture_root / rel
        if full.exists():
            # `.run-state/` may exist if the HALT was after step 10 — we tolerate
            # the directory existing but not artifacts from later stages.
            if rel == "_bmad-output/.run-state":
                continue
            failures.append(f"{rel} should not exist after preflight HALT, but does")

    return failures


# --- Phase 1 assertions ------------------------------------------------------


def assert_phase1_findings_valid(result: DriverResult) -> list[str]:
    """Phase 1.e produced a schema-conformant findings JSON."""
    failures: list[str] = []

    data, err = _read_json(result.fixture_root, PATH_PHASE1_FINDINGS)
    if err:
        return [err]
    assert data is not None

    if data.get("epic_id") not in ("99", 99):
        failures.append(
            f"phase1-findings.json: epic_id={data.get('epic_id')!r}, expected '99'"
        )
    if "scan_at" not in data:
        failures.append("phase1-findings.json: missing scan_at field")
    findings = data.get("findings")
    if not isinstance(findings, list):
        failures.append("phase1-findings.json: findings is not a list")
        return failures

    for i, f in enumerate(findings):
        for required in ("id", "source", "category", "severity", "description"):
            if required not in f:
                failures.append(f"phase1-findings[{i}]: missing required field {required!r}")
        if f.get("severity") not in {"FAIL", "CONCERNS", "INFO"}:
            failures.append(
                f"phase1-findings[{i}]: severity={f.get('severity')!r}, "
                "expected FAIL|CONCERNS|INFO"
            )
        if f.get("source") not in {"unknowns", "edge-case"}:
            failures.append(
                f"phase1-findings[{i}]: source={f.get('source')!r}, "
                "expected unknowns|edge-case"
            )

    return failures


def assert_phase1_headless_all_deferred(result: DriverResult) -> list[str]:
    """Headless mode invariant: every finding is auto-marked deferred,
    EXCEPT FAIL findings (which HALT). T1 happy path has no FAILs, so
    every triage_outcome must be 'deferred'."""
    failures: list[str] = []

    data, err = _read_json(result.fixture_root, PATH_PHASE1_FINDINGS)
    if err:
        return [err]
    assert data is not None

    for i, f in enumerate(data.get("findings", [])):
        outcome = f.get("triage_outcome")
        if outcome != "deferred":
            failures.append(
                f"phase1-findings[{i}]: headless mode should set "
                f"triage_outcome=deferred, got {outcome!r}"
            )
    return failures


def assert_phase1_has_fail_finding(result: DriverResult) -> list[str]:
    """T2: the planted FAIL finding must be present."""
    data, err = _read_json(result.fixture_root, PATH_PHASE1_FINDINGS)
    if err:
        return [err]
    assert data is not None

    fail_findings = [
        f for f in data.get("findings", [])
        if f.get("severity") == "FAIL"
    ]
    if not fail_findings:
        return ["phase1-findings.json: expected at least one FAIL finding, found none"]
    return []


def assert_phase1_halt_blocks_later_phases(result: DriverResult) -> list[str]:
    """T2 invariant (SKILL.md:457): a FAIL HALT in headless mode must NOT
    produce Phase 3 or Phase 4 sidecars."""
    failures: list[str] = []
    forbidden = (
        PATH_TRACEABILITY,
        PATH_GATE_DECISION,
        PATH_NFR_REPORT,
        PATH_CODEX_REPORT,
        PATH_DEFERRED_DELTA,
    )
    for rel in forbidden:
        if _file_exists(result.fixture_root, rel):
            failures.append(
                f"phase1 FAIL HALT should block downstream sidecars, but {rel} exists"
            )
    return failures


# --- Phase 3 / 4 assertions (happy path, T1+T4) ------------------------------


def assert_story_outputs(result: DriverResult) -> list[str]:
    """Each story's AC was satisfied: the expected files exist with the
    expected content. This is the cheapest end-to-end correctness signal."""
    failures: list[str] = []

    cases = (
        ("e2e-tracer.txt", EXPECTED_TRACER_CONTENT, "story 99-1 (tracer)"),
        ("e2e-fanout.txt", EXPECTED_FANOUT_CONTENT, "story 99-2 (fanout)"),
    )
    for rel, expected, label in cases:
        path = result.fixture_root / rel
        if not path.is_file():
            failures.append(f"{label}: expected output file {rel} does not exist")
            continue
        actual = path.read_text()
        if actual != expected:
            failures.append(
                f"{label}: content mismatch. expected={expected!r}, got={actual!r}"
            )
    return failures


def assert_sprint_status_all_done(result: DriverResult) -> list[str]:
    """Every story in the epic flipped to `done` in sprint-status.yaml."""
    failures: list[str] = []

    if not result.sprint_status_snapshots:
        return ["sprint-status: no snapshots captured during run"]

    _, final = result.sprint_status_snapshots[-1]
    for story_key in ("99-1-tracer", "99-2-fanout"):
        actual = final.get(story_key)
        if actual != "done":
            failures.append(
                f"sprint-status: {story_key} final status={actual!r}, expected 'done'"
            )
    return failures


def assert_sprint_status_monotonic(result: DriverResult) -> list[str]:
    """Status transitions never go backward. Order: backlog < ready-for-dev <
    in-progress < done. (And done is terminal.)"""
    failures: list[str] = []

    rank = {"backlog": 0, "ready-for-dev": 1, "in-progress": 2, "done": 3}
    prev: dict[str, int] = {}

    for _ts, snap in result.sprint_status_snapshots:
        for key, status in snap.items():
            r = rank.get(status)
            if r is None:
                continue  # unknown status — don't fail monotonicity on it
            if key in prev and r < prev[key]:
                failures.append(
                    f"sprint-status: {key} regressed from rank {prev[key]} to {r} "
                    f"(status={status!r})"
                )
            prev[key] = max(prev.get(key, 0), r)
    return failures


def assert_phase4_quality_gates(result: DriverResult) -> list[str]:
    """Stage 4.a/4.b ran and produced canonical sidecars with valid statuses."""
    failures: list[str] = []

    # Traceability
    if not _file_exists(result.fixture_root, PATH_TRACEABILITY):
        failures.append(f"{PATH_TRACEABILITY}: missing (Stage 4.a did not run or failed)")

    gate, err = _read_json(result.fixture_root, PATH_GATE_DECISION)
    if err:
        failures.append(err)
    elif gate is not None:
        status = gate.get("gate_status")
        if status not in VALID_TRACE_STATUSES:
            failures.append(
                f"{PATH_GATE_DECISION}: gate_status={status!r}, "
                f"expected one of {sorted(VALID_TRACE_STATUSES)}"
            )

    # NFR — may be skipped if no NFR-touching code. Tolerate either.
    nfr_report_exists = _file_exists(result.fixture_root, PATH_NFR_REPORT)
    nfr_sidecar_exists = _file_exists(result.fixture_root, PATH_NFR_DECISION)
    if nfr_report_exists != nfr_sidecar_exists:
        failures.append(
            f"NFR sidecar/report mismatch: report={nfr_report_exists}, "
            f"sidecar={nfr_sidecar_exists} — both should exist or neither"
        )
    if nfr_sidecar_exists:
        data, err2 = _read_json(result.fixture_root, PATH_NFR_DECISION)
        if err2:
            failures.append(err2)
        elif data and data.get("status") not in VALID_NFR_STATUSES:
            failures.append(
                f"{PATH_NFR_DECISION}: status={data.get('status')!r}, "
                f"expected one of {sorted(VALID_NFR_STATUSES)}"
            )

    return failures


def assert_phase4_codex_review(result: DriverResult) -> list[str]:
    """Stage 4.c either produced a review OR a skip sidecar — never neither."""
    report_exists = _file_exists(result.fixture_root, PATH_CODEX_REPORT)
    skip_exists = _file_exists(result.fixture_root, PATH_CODEX_SKIPPED)

    if not report_exists and not skip_exists:
        return [
            "Stage 4.c: neither epic-99-codex-review.md nor epic-99-codex-skipped.txt "
            "exists. One must be produced (review on git-path, skip if codex unavailable)."
        ]
    if report_exists and skip_exists:
        return [
            "Stage 4.c: both review and skip sidecars exist — mutually exclusive"
        ]
    return []


def assert_phase4_deferred_delta(result: DriverResult) -> list[str]:
    """Stage 4.d ran."""
    if not _file_exists(result.fixture_root, PATH_DEFERRED_DELTA):
        return [f"{PATH_DEFERRED_DELTA}: missing (Stage 4.d did not run)"]
    return []


def assert_digest_rendered(result: DriverResult) -> list[str]:
    """Stage 4.e ran and the digest references the major sidecars."""
    failures: list[str] = []

    run_state = result.fixture_root / "_bmad-output" / ".run-state"
    digests = sorted(run_state.glob("run-digest-*.md")) if run_state.is_dir() else []
    if not digests:
        return ["run-digest-<runId>.md: not produced (Stage 4.e did not complete)"]
    digest = digests[-1].read_text()

    # The digest should reference each major sidecar's filename. We check
    # for filename substrings rather than full paths to tolerate small
    # composition variations.
    for needle in (
        "traceability-matrix.md",
        "deferred-delta.md",
    ):
        if needle not in digest:
            failures.append(f"digest does not reference {needle}")
    return failures


def assert_no_orphan_halt_sidecars(result: DriverResult) -> list[str]:
    """Happy path: no `quick-dev-halt-*.json` sidecars should exist."""
    run_state = result.fixture_root / "_bmad-output" / ".run-state"
    if not run_state.is_dir():
        return []
    orphans = list(run_state.glob("quick-dev-halt-*.json"))
    if orphans:
        return [
            f"unexpected HALT sidecars on happy path: "
            f"{[p.name for p in orphans]}"
        ]
    return []


def assert_per_story_end_shas(result: DriverResult) -> list[str]:
    """Each story produced its `epic-99-story-<id>-end.sha` sidecar
    (Stage 3.4 records this on completion)."""
    failures: list[str] = []
    for story in ("99-1", "99-2"):
        rel = f"_bmad-output/.run-state/epic-99-story-{story}-end.sha"
        if not _file_exists(result.fixture_root, rel):
            failures.append(
                f"{rel}: missing — story may not have flipped to 'done' cleanly"
            )
    return failures


# --- T4 (Express) signposting check ------------------------------------------


def assert_express_consent_prompt_shown(result: DriverResult) -> list[str]:
    """T4: the Express signposting block + [y/N] consent prompt appeared."""
    pane = result.pane_capture
    needles = (
        "Express mode will",
        "Proceed?",
        "dangerously-skip-permissions",
    )
    failures = [
        f"Express consent gate: pane missing expected text {n!r}"
        for n in needles if n not in pane
    ]
    return failures


# --- Composite assertion bundles ---------------------------------------------


def all_failures(*assertion_results: Iterable[str]) -> list[str]:
    """Flatten failures from multiple assertion calls. Convenience for tests."""
    out: list[str] = []
    for batch in assertion_results:
        out.extend(batch)
    return out


def t1_happy_headless_assertions(result: DriverResult) -> list[str]:
    """Composite assertion bundle for T1."""
    return all_failures(
        assert_phase1_findings_valid(result),
        assert_phase1_headless_all_deferred(result),
        assert_story_outputs(result),
        assert_sprint_status_all_done(result),
        assert_sprint_status_monotonic(result),
        assert_per_story_end_shas(result),
        assert_phase4_quality_gates(result),
        assert_phase4_codex_review(result),
        assert_phase4_deferred_delta(result),
        assert_digest_rendered(result),
        assert_no_orphan_halt_sidecars(result),
    )


def t2_phase1_fail_halt_assertions(result: DriverResult) -> list[str]:
    """Composite assertion bundle for T2."""
    return all_failures(
        assert_phase1_findings_valid(result),
        assert_phase1_has_fail_finding(result),
        assert_phase1_halt_blocks_later_phases(result),
    )


def t3_preflight_halt_assertions(result: DriverResult) -> list[str]:
    """Composite assertion bundle for T3."""
    return assert_preflight_halt(result)


def t4_express_consent_assertions(result: DriverResult) -> list[str]:
    """Composite assertion bundle for T4 = T1 + Express signposting check."""
    return all_failures(
        assert_express_consent_prompt_shown(result),
        t1_happy_headless_assertions(result),
    )
