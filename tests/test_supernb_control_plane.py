from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
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
run_control_plane = load_module("supernb_run_test", "scripts/supernb-run.py")


class SupernbControlPlaneTests(unittest.TestCase):
    def test_delivery_docs_only_commit_is_not_completion_grade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            project_dir = root / "project"
            packet_dir.mkdir()
            project_dir.mkdir()

            subprocess.run(["git", "-C", str(project_dir), "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "config", "user.name", "Supernb Test"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "config", "user.email", "supernb@example.com"], check=True, capture_output=True, text=True)

            (project_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project_dir), "add", "README.md"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "commit", "-m", "chore: initial"], check=True, capture_output=True, text=True)
            git_before = execute_next.git_state(project_dir)

            plan_path = project_dir / ".supernb" / "plans" / "demo" / "implementation-plan.md"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text("# Updated plan\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project_dir), "add", str(plan_path.relative_to(project_dir))], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "commit", "-m", "docs: update delivery plan"], check=True, capture_output=True, text=True)
            git_after = execute_next.git_state(project_dir)
            created_commits = execute_next.commits_created(project_dir, git_before, git_after)

            response_text = (
                f"{execute_next.REPORT_START}\n"
                + json.dumps(
                    {
                        "completion_status": "completed",
                        "summary": "Completed one delivery batch.",
                        "completed_items": ["Updated implementation documentation."],
                        "remaining_items": [],
                        "evidence_artifacts": [],
                        "artifacts_updated": [str(plan_path.relative_to(project_dir))],
                        "commands_run": [],
                        "tests_run": ["npm test -- --runInBand"],
                        "validated_batches_completed": 1,
                        "batch_commits": [],
                        "workflow_trace": {
                            "brainstorming": {"used": False, "evidence": "Not needed."},
                            "writing_plans": {"used": True, "evidence": "Updated the implementation plan."},
                            "test_driven_development": {"used": True, "evidence": "Ran the documented delivery test flow."},
                            "code_review": {"used": True, "evidence": "Reviewed the documented changes."},
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
                harness="codex",
                status="succeeded",
                dry_run=False,
                exit_code=0,
                response_text=response_text,
                stderr_text="npm test -- --runInBand\n",
                packet_dir=packet_dir,
                project_dir=project_dir,
                phase_readiness={"ready_for_certification": True},
                git_before=git_before,
                git_after=git_after,
                created_commits=created_commits,
            )

            self.assertEqual(suggestion["suggested_result_status"], "needs-follow-up")
            self.assertTrue(
                any("did not modify any product workspace files" in issue for issue in suggestion["workflow_issues"])
            )

    def test_delivery_product_file_commit_can_remain_completion_grade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            project_dir = root / "project"
            packet_dir.mkdir()
            project_dir.mkdir()

            subprocess.run(["git", "-C", str(project_dir), "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "config", "user.name", "Supernb Test"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "config", "user.email", "supernb@example.com"], check=True, capture_output=True, text=True)

            app_path = project_dir / "src" / "app.ts"
            app_path.parent.mkdir(parents=True, exist_ok=True)
            app_path.write_text("export const version = 1;\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project_dir), "add", str(app_path.relative_to(project_dir))], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(project_dir), "commit", "-m", "feat: initial app"], check=True, capture_output=True, text=True)
            git_before = execute_next.git_state(project_dir)

            app_path.write_text("export const version = 2;\n", encoding="utf-8")
            release_path = project_dir / ".supernb" / "releases" / "demo" / "release-readiness.md"
            release_path.parent.mkdir(parents=True, exist_ok=True)
            release_path.write_text("# Release readiness\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(project_dir), "add", str(app_path.relative_to(project_dir)), str(release_path.relative_to(project_dir))],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(["git", "-C", str(project_dir), "commit", "-m", "feat: ship delivery batch"], check=True, capture_output=True, text=True)
            git_after = execute_next.git_state(project_dir)
            created_commits = execute_next.commits_created(project_dir, git_before, git_after)

            response_text = (
                f"{execute_next.REPORT_START}\n"
                + json.dumps(
                    {
                        "completion_status": "completed",
                        "summary": "Completed one delivery batch.",
                        "completed_items": ["Implemented the requested delivery batch."],
                        "remaining_items": [],
                        "evidence_artifacts": [],
                        "artifacts_updated": [str(app_path.relative_to(project_dir)), str(release_path.relative_to(project_dir))],
                        "commands_run": [],
                        "tests_run": ["npm test -- --runInBand"],
                        "validated_batches_completed": 1,
                        "batch_commits": [],
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
                harness="codex",
                status="succeeded",
                dry_run=False,
                exit_code=0,
                response_text=response_text,
                stderr_text="npm test -- --runInBand\n",
                packet_dir=packet_dir,
                project_dir=project_dir,
                phase_readiness={"ready_for_certification": True},
                git_before=git_before,
                git_after=git_after,
                created_commits=created_commits,
            )

            self.assertEqual(suggestion["suggested_result_status"], "succeeded")
            self.assertFalse(
                any("did not modify any product workspace files" in issue for issue in suggestion["workflow_issues"])
            )

    def test_run_command_strings_use_absolute_supernb_cli_path(self) -> None:
        initiative_id = "2026-03-19-demo"
        expected_prefix = str((ROOT_DIR / "scripts" / "supernb").resolve())

        commands = [
            run_control_plane.record_result_command(initiative_id, "delivery"),
            run_control_plane.advance_phase_command(initiative_id, "delivery"),
            run_control_plane.certify_phase_command(initiative_id, "delivery"),
            run_control_plane.execute_next_command(initiative_id),
            run_control_plane.apply_execution_command(initiative_id),
        ]

        for command in commands:
            self.assertIn(expected_prefix, command)
            self.assertNotIn("./scripts/supernb", command)

    def test_certification_report_labels_gate_status_as_post_pass_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project_dir = root / "product"
            project_dir.mkdir(parents=True, exist_ok=True)
            report_path = root / "certification.md"
            spec = {
                "initiative": {"id": "2026-03-19-demo"},
                "delivery": {"project_dir": str(project_dir)},
                "artifacts": {
                    "research_dir": ".supernb/research/2026-03-19-demo",
                    "phase_results_dir": ".supernb/initiatives/2026-03-19-demo/phase-results",
                },
            }
            readiness = {
                "ready_for_certification": False,
                "summary": "Needs follow-up",
                "total_missing_sections": 0,
                "total_thin_sections": 0,
                "total_placeholders": 0,
                "total_semantic_issues": 1,
                "total_traceability_issues": 0,
                "artifact_checks": [],
                "traceability_checks": [],
            }

            certify_phase.DISPLAY_ROOTS = [project_dir, ROOT_DIR]
            certify_phase.write_report(
                spec=spec,
                phase="research",
                issues=[],
                execution_findings=[],
                readiness=readiness,
                report_path=report_path,
                applied=False,
            )

            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("- Gate status to apply after pass: `approved`", report_text)
            self.assertNotIn("- Recommended gate status: `approved`", report_text)

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

    def test_wait_for_loop_audit_summary_finalizes_removed_state_after_watcher_race(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            packet_dir.mkdir()
            loop_contract = {
                "state_file": root / "project" / ".claude" / "superpower-loop-demo.local.md",
                "audit_summary_file": packet_dir / "ralph-loop-audit.json",
                "audit_events_file": packet_dir / "ralph-loop-audit.ndjson",
                "completion_promise": "SUPERNB demo planning batch complete",
                "max_iterations": 6,
                "session_id": "session-demo",
                "prompt_file": packet_dir / "ralph-loop-prompt.md",
                "plugin_dir": ROOT_DIR / "bundles" / "claude-loop-marketplace" / "supernb-loop" / ".claude-plugin",
                "start_command": [],
                "start_command_text": "",
            }

            execute_next.write_json(
                loop_contract["audit_summary_file"],
                {
                    "state_file": str(loop_contract["state_file"]),
                    "completion_promise": loop_contract["completion_promise"],
                    "expected_session_id": loop_contract["session_id"],
                    "state_observed": True,
                    "removed_after_observation": False,
                    "last_iteration": 1,
                    "last_session_id": loop_contract["session_id"],
                    "final_status": "watching",
                },
            )

            payload = execute_next.wait_for_loop_audit_summary(loop_contract, timeout_seconds=0.1)
            self.assertIsNotNone(payload)
            self.assertEqual(payload.get("final_status"), "state_removed")
            self.assertTrue(payload.get("removed_after_observation"))
            self.assertTrue((packet_dir / "ralph-loop-audit.ndjson").is_file())

    def test_wait_for_loop_state_observed_returns_after_watcher_observes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            packet_dir = root / "packet"
            state_dir = root / "project" / ".claude"
            packet_dir.mkdir()
            state_dir.mkdir(parents=True)
            state_file = state_dir / "superpower-loop-demo.local.md"
            state_file.write_text(
                "---\n"
                'session_id: "session-demo"\n'
                'completion_promise: "SUPERNB demo planning batch complete"\n'
                'iteration: "1"\n'
                'started_at: "2026-03-20T00:00:00Z"\n'
                "---\n",
                encoding="utf-8",
            )
            loop_contract = {
                "state_file": state_file,
                "audit_summary_file": packet_dir / "ralph-loop-audit.json",
                "audit_events_file": packet_dir / "ralph-loop-audit.ndjson",
                "completion_promise": "SUPERNB demo planning batch complete",
                "max_iterations": 6,
                "session_id": "session-demo",
                "prompt_file": packet_dir / "ralph-loop-prompt.md",
                "plugin_dir": ROOT_DIR / "bundles" / "claude-loop-marketplace" / "supernb-loop" / ".claude-plugin",
                "start_command": [],
                "start_command_text": "",
            }

            execute_next.write_json(
                loop_contract["audit_summary_file"],
                {
                    "state_file": str(state_file),
                    "completion_promise": loop_contract["completion_promise"],
                    "expected_session_id": loop_contract["session_id"],
                    "state_observed": False,
                    "removed_after_observation": False,
                    "last_iteration": 0,
                    "last_session_id": "",
                    "final_status": "watching",
                },
            )

            def mark_observed() -> None:
                execute_next.write_json(
                    loop_contract["audit_summary_file"],
                    {
                        "state_file": str(state_file),
                        "completion_promise": loop_contract["completion_promise"],
                        "expected_session_id": loop_contract["session_id"],
                        "state_observed": True,
                        "removed_after_observation": False,
                        "last_iteration": 1,
                        "last_session_id": loop_contract["session_id"],
                        "final_status": "watching",
                    },
                )

            timer = threading.Timer(0.05, mark_observed)
            timer.start()
            try:
                payload = execute_next.wait_for_loop_state_observed(loop_contract, timeout_seconds=0.5)
            finally:
                timer.cancel()

            self.assertIsNotNone(payload)
            self.assertTrue(payload.get("state_observed"))
            self.assertEqual(payload.get("last_session_id"), loop_contract["session_id"])


if __name__ == "__main__":
    unittest.main()
