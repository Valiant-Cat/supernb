# Supernb Control Plane Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the control-plane gaps that allow supernb phase state, certification, execution closeout, and release evidence to drift away from the real repository state.

**Architecture:** Harden the existing Python control plane rather than replacing it. Add failing tests around phase-state drift, manual closeout shortcuts, template-grade artifacts, and weak release evidence; then tighten `run`, `certify-phase`, `record-result`, `apply-execution`, and prompt-first artifact generation so the same repository cannot appear simultaneously incomplete and releasable.

**Tech Stack:** Python 3 scripts, unittest-based control-plane tests, Markdown/JSON initiative artifacts

---

### Task 1: Add failing tests for state drift and weak completion criteria

**Files:**
- Modify: `tests/test_supernb_control_plane.py`
- Test: `tests/test_supernb_control_plane.py`

- [ ] **Step 1: Write failing tests for phase-state drift**

Add tests that prove:
- `run` must not mark a phase healthy when certification disagrees with the phase metadata.
- stale or template-grade research/PRD/design/planning/release artifacts should block downstream status.
- release should not look complete when verification evidence is missing or obviously placeholder-grade.

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python -m unittest tests.test_supernb_control_plane.SupernbControlPlaneTests`
Expected: FAIL in the newly added cases.

- [ ] **Step 3: Write minimal control-plane changes**

Touch only the code needed to make those tests pass:
- `scripts/supernb-run.py`
- `scripts/supernb-certify-phase.py`
- `scripts/lib/supernb_common.py`

- [ ] **Step 4: Re-run the targeted tests**

Run: `python -m unittest tests.test_supernb_control_plane.SupernbControlPlaneTests`
Expected: PASS for the new cases and existing nearby cases.

### Task 2: Add failing tests for prompt-first closeout and manual override loopholes

**Files:**
- Modify: `tests/test_supernb_cli_integration.py`
- Test: `tests/test_supernb_cli_integration.py`

- [ ] **Step 1: Write failing integration tests**

Cover these cases:
- prompt-first closeout should fail when reassessment is still pending or template-grade.
- imported/apply execution should not leave `run-status` in a contradictory state.
- manual result recording should be blocked for phases that still have upstream drift or missing verification evidence.

- [ ] **Step 2: Run targeted integration tests to verify RED**

Run: `python -m unittest tests.test_supernb_cli_integration.SupernbCliIntegrationTests`
Expected: FAIL in the new cases.

- [ ] **Step 3: Implement the minimal fixes**

Modify:
- `scripts/supernb-prompt-sync.py`
- `scripts/supernb-prompt-closeout.py`
- `scripts/supernb-apply-execution.py`
- `scripts/supernb-record-result.py`

- [ ] **Step 4: Re-run targeted integration tests**

Run: `python -m unittest tests.test_supernb_cli_integration.SupernbCliIntegrationTests`
Expected: PASS for the new cases.

### Task 3: Reduce template-grade artifacts and strengthen release evidence requirements

**Files:**
- Modify: `scripts/supernb-prompt-sync.py`
- Modify: `scripts/supernb-execute-next.py`
- Modify: `templates/` files only if required by generator behavior
- Test: `tests/test_supernb_control_plane.py`

- [ ] **Step 1: Add failing tests for template minimization and release evidence**

Cover:
- generated reassessment/report templates should not incentivize obviously empty placeholders.
- release readiness should require explicit verification fields and distinguish repo-ready vs release-ready.
- planning/delivery should not self-certify without concrete execution evidence.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `python -m unittest tests.test_supernb_control_plane.SupernbControlPlaneTests`
Expected: FAIL in the new cases.

- [ ] **Step 3: Implement minimal generator and readiness changes**

Make template output more constrained and update readiness checks accordingly.

- [ ] **Step 4: Re-run the focused tests**

Run: `python -m unittest tests.test_supernb_control_plane.SupernbControlPlaneTests`
Expected: PASS.

### Task 4: Final verification and repository closeout

**Files:**
- Review: `scripts/*.py`, `scripts/lib/supernb_common.py`, `tests/*.py`, updated plan doc if needed

- [ ] **Step 1: Run the full supernb test suite**

Run: `python -m unittest tests.test_supernb_control_plane tests.test_supernb_cli_integration`
Expected: PASS.

- [ ] **Step 2: Run repository-level verification command if available**

Run: `make test`
Expected: PASS or document any non-supernb-only failure.

- [ ] **Step 3: Review the diff for policy regressions**

Check for:
- new manual-override loopholes
- hidden placeholder defaults
- contradictory release statuses
- brittle test fixtures

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-03-22-supernb-control-plane-hardening.md scripts tests
git commit -m "Harden supernb control plane consistency"
```
