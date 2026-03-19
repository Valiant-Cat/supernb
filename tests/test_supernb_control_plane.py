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


if __name__ == "__main__":
    unittest.main()
