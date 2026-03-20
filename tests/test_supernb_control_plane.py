from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module(name: str, relative_path: str):
    module_path = ROOT_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


common = load_module("supernb_common_test", "scripts/lib/supernb_common.py")
execute_next = load_module("supernb_execute_next_test", "scripts/supernb-execute-next.py")
certify_phase = load_module("supernb_certify_phase_test", "scripts/supernb-certify-phase.py")


class SupernbControlPlaneTests(unittest.TestCase):
    def test_normalized_snapshot_ignores_gate_metadata_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pending = Path(tmp_dir) / "pending.md"
            approved = Path(tmp_dir) / "approved.md"

            pending.write_text(
                "# Artifact\n\n"
                "- Approval status: pending\n"
                "- Ready for execution: no\n"
                "- Delivery status: pending\n"
                "\n## Body\n\nDetailed content.\n",
                encoding="utf-8",
            )
            approved.write_text(
                "# Artifact\n\n"
                "- Approval status: approved\n"
                "- Ready for execution: yes\n"
                "- Delivery status: verified\n"
                "\n## Body\n\nDetailed content.\n",
                encoding="utf-8",
            )

            self.assertEqual(
                common.normalized_snapshot_bytes(pending),
                common.normalized_snapshot_bytes(approved),
            )

    def test_resolve_prompt_path_uses_project_workspace_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "product"
            project_dir.mkdir(parents=True, exist_ok=True)
            spec = {
                "delivery": {"project_dir": str(project_dir)},
                "artifacts": {"next_command_md": ".supernb/initiatives/demo/next-command.md"},
            }

            args = argparse.Namespace(prompt_file=None)
            resolved = execute_next.resolve_prompt_path(args, {"next_command": {}}, spec)

            self.assertEqual(
                resolved,
                (project_dir / ".supernb" / "initiatives" / "demo" / "next-command.md").resolve(),
            )

    def test_latest_execution_packet_prefers_real_run_over_newer_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            executions_dir = root / "executions"
            executions_dir.mkdir(parents=True, exist_ok=True)
            spec = {
                "initiative": {"id": "2026-03-19-demo"},
                "delivery": {"project_dir": str(root / "product")},
                "artifacts": {"executions_dir": str(executions_dir)},
            }

            real_packet = executions_dir / "20260319-100000-delivery-codex"
            real_packet.mkdir()
            (real_packet / "request.json").write_text(
                json.dumps(
                    {
                        "initiative_id": "2026-03-19-demo",
                        "phase": "delivery",
                        "dry_run": False,
                    }
                ),
                encoding="utf-8",
            )
            (real_packet / "result-suggestion.json").write_text(
                json.dumps({"execution_status": "succeeded", "suggested_result_status": "succeeded"}),
                encoding="utf-8",
            )

            dry_run_packet = executions_dir / "20260319-110000-delivery-codex"
            dry_run_packet.mkdir()
            (dry_run_packet / "request.json").write_text(
                json.dumps(
                    {
                        "initiative_id": "2026-03-19-demo",
                        "phase": "delivery",
                        "dry_run": True,
                    }
                ),
                encoding="utf-8",
            )
            (dry_run_packet / "result-suggestion.json").write_text(
                json.dumps({"execution_status": "prepared", "suggested_result_status": "not-run"}),
                encoding="utf-8",
            )

            os.utime(real_packet, (1_700_000_000, 1_700_000_000))
            os.utime(dry_run_packet, (1_800_000_000, 1_800_000_000))

            selected = certify_phase.latest_execution_packet(spec, "delivery")
            self.assertEqual(selected.resolve(), real_packet.resolve())

    def test_direct_run_without_report_json_is_not_certifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            project_dir = root / "project"
            packet_dir.mkdir()
            project_dir.mkdir()

            suggestion = execute_next.build_result_suggestion(
                phase="delivery",
                harness="codex",
                status="succeeded",
                dry_run=False,
                exit_code=0,
                response_text="Implemented the requested batch and updated files.",
                stderr_text="",
                packet_dir=packet_dir,
                project_dir=project_dir,
                phase_readiness={"ready_for_certification": True},
                git_before={"is_repo": False},
                git_after={"is_repo": False},
                created_commits=[],
            )

            self.assertEqual(suggestion["source"], "heuristic-missing-structured-report")
            self.assertEqual(suggestion["suggested_result_status"], "needs-follow-up")
            self.assertIn("REPORT JSON block", "\n".join(suggestion["workflow_issues"]))

    def test_design_semantic_checks_require_deeper_impeccable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "ui-ux-spec.md"
            path.write_text(
                "# UI UX Spec\n\n"
                "## Design Context\n\n"
                "- Target audience: Busy professionals\n"
                "- Use cases: Daily finance tracking\n"
                "- Brand tone: Calm and premium\n"
                "- Differentiation goal: Less clutter\n"
                "- Product maturity target: 10M DAU\n\n"
                "## Product Experience Strategy\n\n"
                "- Primary promise to the user: Clarity\n"
                "- Emotional tone: Confident\n"
                "- Trust-building strategy: Transparent data\n"
                "- Key moments that must feel premium: Onboarding and insights\n\n"
                "## Visual Direction\n\n"
                "- Aesthetic direction: Editorial\n"
                "- Typography system: Display + text pairing\n"
                "- Color system: Warm neutrals with signal accents\n"
                "- Motion principles: Calm transitions\n"
                "- Density and spacing strategy: Spacious default\n\n"
                "## Accessibility And Readability Rules\n\n"
                "- Minimum contrast expectations: AA+\n"
                "- CTA readability rules: Solid fill only\n"
                "- Disabled/loading state rules: Distinct opacity\n"
                "- Focus state rules: Visible rings\n"
                "- Touch target and mobile ergonomics rules: 44pt+\n\n"
                "## Localization And Copy Rules\n\n"
                "- Source locale: en\n"
                "- Target locales: en, ja\n"
                "- Copy must be referenced from localization resources, not hardcoded in UI code.\n"
                "- Long-text expansion and multi-locale layout considerations: Reserve width\n"
                "- Tone and terminology rules: Plain language\n\n"
                "## Information Architecture\n\n"
                "- Primary navigation: Bottom nav\n"
                "- Secondary navigation: Context tabs\n"
                "- Key page groups: Home, insights, account\n"
                "- Entry points and conversion paths: Home to upgrade\n\n"
                "## User Flow Coverage\n\n"
                "- Acquisition or entry flow: Store to onboarding\n"
                "- Activation flow: Connect account\n"
                "- Core repeat-use flow: Daily dashboard\n"
                "- Upgrade / conversion flow: Insight paywall\n"
                "- Recovery or support flow: Contact support\n\n"
                "## Page Specs\n\n"
                "### Page 1\n\n"
                "- Purpose: Dashboard\n"
                "- Core modules: Snapshot, trend card\n"
                "- Primary CTA: Connect account\n"
                "- Empty/loading/error/success states: All covered\n\n"
                "### Page 2\n\n"
                "- Purpose: Insights\n"
                "- Core modules: Charts, commentary\n"
                "- Primary CTA: Upgrade\n"
                "- Empty/loading/error/success states: All covered\n\n"
                "### Page 3\n\n"
                "- Purpose: Account\n"
                "- Core modules: Settings, support\n"
                "- Primary CTA: Manage plan\n"
                "- Empty/loading/error/success states: All covered\n\n"
                "## State Matrix\n\n"
                "| Surface | Empty state | Loading state | Error state | Success state | Trust or guidance cue |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| Dashboard | Empty | Loading | Error | Success | Security badge |\n"
                "| Insights | Empty | Loading | Error | Success | Explainability |\n"
                "| Upgrade | Empty | Loading | Error | Success | Billing note |\n\n"
                "## Component Rules\n\n"
                "- Buttons: Priority scale\n"
                "- Forms: Inline validation\n"
                "- Cards: Clear hierarchy\n"
                "- Lists: Readable rows\n"
                "- Modals: Sparse use\n"
                "- Navigation: Persistent anchors\n"
                "- Data visualization or rich content: Legible charts\n\n"
                "## Responsive And Platform Behavior\n\n"
                "- Mobile adaptation rules: Native bottom sheet\n"
                "- Tablet / desktop rules: Multi-column layout\n"
                "- Input mode differences: Hover on desktop\n"
                "- Performance or motion constraints: Reduce on low-end devices\n\n"
                "## Trust And Feedback Cues\n\n"
                "- Security / privacy cues: Encryption notices\n"
                "- Progress feedback: Predictive progress\n"
                "- Error recovery guidance: Inline recovery steps\n"
                "- Empty-state education: Teach value\n\n"
                "## Scale UX Requirements\n\n"
                "- Onboarding for broad-market conversion: Fast first-run\n"
                "- Habit / repeat-use surfaces: Daily streak cues\n"
                "- Power-user efficiency surfaces: Saved views\n"
                "- Localization and market adaptation surfaces: Region-specific copy\n"
                "- Support / trust / abuse-reporting entry points: Reachable support\n\n"
                "## Impeccable Review Notes\n\n"
                "- Audit findings: Strong baseline\n"
                "- Critique findings: Improve trust density\n"
                "- Polish actions: Refine spacing\n"
                "- Anti-patterns explicitly avoided: Generic cards\n",
                encoding="utf-8",
            )

            sections = execute_next.level2_sections(path.read_text(encoding="utf-8"))
            issues, _metrics = execute_next.semantic_checks_for_artifact(path, "design", sections)
            combined = "\n".join(issues)

            self.assertIn("Key Journey Surface Deep Dives", combined)
            self.assertIn("Design System Definition", combined)
            self.assertIn("Conversion And Retention Surfaces", combined)

    def test_traceability_checks_flag_cross_phase_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project_dir = root / "product"
            initiative_id = "2026-03-19-demo"
            prd_dir = project_dir / ".supernb" / "prd" / initiative_id
            design_dir = project_dir / ".supernb" / "design" / initiative_id
            prd_dir.mkdir(parents=True, exist_ok=True)
            design_dir.mkdir(parents=True, exist_ok=True)

            (prd_dir / "product-requirements.md").write_text(
                "# PRD\n\n"
                "## Cross-Phase Traceability Matrix\n\n"
                "| Trace ID | Research insight or review theme | PRD capability | Primary design surface | Planned delivery batch | Release validation |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| TR-001 | Users hate manual setup | Smart onboarding | Onboarding flow | Batch 1 | Activation QA |\n"
                "| TR-002 | Users want trusted insights | Insight feed | Insight dashboard | Batch 2 | Insight regression |\n",
                encoding="utf-8",
            )
            (design_dir / "ui-ux-spec.md").write_text(
                "# UI UX Spec\n\n"
                "## Traceability To Research And PRD\n\n"
                "| Trace ID | PRD capability | Research insight reference | Primary design surface | Key states or edge cases | Impeccable evidence |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                "| TR-001 | Smart onboarding | Users hate manual setup | Welcome tour | Empty/loading/error | Audit v1 |\n",
                encoding="utf-8",
            )

            spec = {
                "initiative": {"id": initiative_id},
                "delivery": {"project_dir": str(project_dir)},
                "artifacts": {
                    "prd_dir": ".supernb/prd/2026-03-19-demo",
                    "design_dir": ".supernb/design/2026-03-19-demo",
                },
            }

            checks = execute_next.build_traceability_checks(spec, "design")
            issues = [issue for check in checks for issue in check.get("issues", [])]

            self.assertTrue(any("missing source rows" in issue for issue in issues))
            self.assertTrue(any("TR-002" in issue for issue in issues))
            self.assertTrue(any("changes primary surfaces" in issue for issue in issues))
            self.assertTrue(any("Welcome tour" in issue for issue in issues))

    def test_claude_delivery_without_loop_evidence_is_not_certifiable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            project_dir = root / "project"
            packet_dir.mkdir()
            project_dir.mkdir()

            response_text = (
                f"{execute_next.REPORT_START}\n"
                + json.dumps(
                    {
                        "completion_status": "completed",
                        "summary": "Completed one delivery batch.",
                        "completed_items": ["Implemented the requested delivery batch."],
                        "remaining_items": [],
                        "evidence_artifacts": [],
                        "artifacts_updated": [],
                        "commands_run": [],
                        "tests_run": [],
                        "validated_batches_completed": 1,
                        "batch_commits": ["abc123 delivery batch"],
                        "workflow_trace": {
                            "brainstorming": {"used": False, "evidence": "Not needed."},
                            "writing_plans": {"used": True, "evidence": "Updated the implementation plan."},
                            "test_driven_development": {"used": True, "evidence": "Wrote and ran the delivery test first."},
                            "code_review": {"used": True, "evidence": "Reviewed the completed batch."},
                            "using_git_worktrees": {"used": False, "evidence": "Not needed for this batch."},
                            "subagent_or_executing_plans": {"used": True, "evidence": "Executed a single bounded batch."},
                        },
                        "loop_execution": {
                            "used": False,
                            "mode": "none",
                            "completion_promise": "",
                            "state_file": "",
                            "max_iterations": 0,
                            "final_iteration": 0,
                            "exit_reason": "",
                            "evidence": "",
                        },
                        "recommended_result_status": "succeeded",
                        "recommended_gate_action": "certify",
                        "recommended_gate_status": "verified",
                        "follow_up": [],
                    },
                    indent=2,
                )
                + f"\n{execute_next.REPORT_END}\n"
            )

            suggestion = execute_next.build_result_suggestion(
                phase="delivery",
                harness="claude-code-prompt",
                status="succeeded",
                dry_run=False,
                exit_code=0,
                response_text=response_text,
                stderr_text="",
                packet_dir=packet_dir,
                project_dir=project_dir,
                phase_readiness={"ready_for_certification": True},
                git_before={"is_repo": False},
                git_after={"is_repo": False},
                created_commits=[],
            )

            self.assertEqual(suggestion["suggested_result_status"], "needs-follow-up")
            self.assertTrue(any("Ralph Loop" in issue for issue in suggestion["workflow_issues"]))

    def test_claude_delivery_requires_audit_backed_loop_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            project_dir = root / "project"
            packet_dir.mkdir()
            project_dir.mkdir()
            audit_summary = packet_dir / "ralph-loop-audit.json"
            audit_summary.write_text(
                json.dumps(
                    {
                        "state_file": str(project_dir / ".claude" / "superpower-loop-demo.local.md"),
                        "completion_promise": "SUPERNB demo delivery batch complete",
                        "max_iterations": 8,
                        "expected_session_id": "session-1",
                        "state_observed": True,
                        "removed_after_observation": False,
                        "last_iteration": 1,
                        "last_session_id": "session-1",
                        "final_status": "timeout",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            response_text = (
                f"{execute_next.REPORT_START}\n"
                + json.dumps(
                    {
                        "completion_status": "completed",
                        "summary": "Completed one delivery batch.",
                        "completed_items": ["Implemented the requested delivery batch."],
                        "remaining_items": [],
                        "evidence_artifacts": [str(audit_summary)],
                        "artifacts_updated": [],
                        "commands_run": [],
                        "tests_run": [],
                        "validated_batches_completed": 1,
                        "batch_commits": ["abc123 delivery batch"],
                        "workflow_trace": {
                            "brainstorming": {"used": False, "evidence": "Not needed."},
                            "writing_plans": {"used": True, "evidence": "Updated the implementation plan."},
                            "test_driven_development": {"used": True, "evidence": "Wrote and ran the delivery test first."},
                            "code_review": {"used": True, "evidence": "Reviewed the completed batch."},
                            "using_git_worktrees": {"used": False, "evidence": "Not needed for this batch."},
                            "subagent_or_executing_plans": {"used": True, "evidence": "Executed a single bounded batch."},
                        },
                        "loop_execution": {
                            "used": True,
                            "mode": "ralph-loop",
                            "completion_promise": "SUPERNB demo delivery batch complete",
                            "state_file": str(project_dir / ".claude" / "superpower-loop-demo.local.md"),
                            "max_iterations": 8,
                            "final_iteration": 1,
                            "exit_reason": "completion promise became true",
                            "evidence": str(audit_summary),
                        },
                        "recommended_result_status": "succeeded",
                        "recommended_gate_action": "certify",
                        "recommended_gate_status": "verified",
                        "follow_up": [],
                    },
                    indent=2,
                )
                + f"\n{execute_next.REPORT_END}\n"
            )

            suggestion = execute_next.build_result_suggestion(
                phase="delivery",
                harness="claude-code-prompt",
                status="succeeded",
                dry_run=False,
                exit_code=0,
                response_text=response_text,
                stderr_text="",
                packet_dir=packet_dir,
                project_dir=project_dir,
                phase_readiness={"ready_for_certification": True},
                git_before={"is_repo": False},
                git_after={"is_repo": False},
                created_commits=[],
            )

            self.assertEqual(suggestion["suggested_result_status"], "needs-follow-up")
            combined = "\n".join(suggestion["workflow_issues"])
            self.assertIn("did not observe the state file being removed", combined)
            self.assertIn("final_status must be state_removed", combined)


if __name__ == "__main__":
    unittest.main()
