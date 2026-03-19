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


if __name__ == "__main__":
    unittest.main()
