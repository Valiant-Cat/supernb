from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def write_spec(root: Path, initiative_id: str = "2026-03-19-demo") -> dict[str, Path]:
    project_dir = root / "product"
    initiative_root = project_dir / ".supernb" / "initiatives" / initiative_id
    spec_path = initiative_root / "initiative.yaml"
    research_dir = project_dir / ".supernb" / "research" / initiative_id
    prd_dir = project_dir / ".supernb" / "prd" / initiative_id
    design_dir = project_dir / ".supernb" / "design" / initiative_id
    plan_dir = project_dir / ".supernb" / "plans" / initiative_id
    release_dir = project_dir / ".supernb" / "releases" / initiative_id
    command_briefs_dir = initiative_root / "command-briefs"
    phase_results_dir = initiative_root / "phase-results"
    executions_dir = initiative_root / "executions"

    for directory in [
        initiative_root,
        research_dir,
        prd_dir,
        design_dir,
        plan_dir,
        release_dir,
        command_briefs_dir,
        phase_results_dir,
        executions_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    spec_text = f"""
initiative:
  id: "{initiative_id}"
delivery:
  project_dir: "{project_dir}"
artifacts:
  run_status_md: ".supernb/initiatives/{initiative_id}/run-status.md"
  run_status_json: ".supernb/initiatives/{initiative_id}/run-status.json"
  run_log_md: ".supernb/initiatives/{initiative_id}/run-log.md"
  command_briefs_dir: ".supernb/initiatives/{initiative_id}/command-briefs"
  phase_results_dir: ".supernb/initiatives/{initiative_id}/phase-results"
  executions_dir: ".supernb/initiatives/{initiative_id}/executions"
  certification_state_json: ".supernb/initiatives/{initiative_id}/certification-state.json"
  research_dir: ".supernb/research/{initiative_id}"
  prd_dir: ".supernb/prd/{initiative_id}"
  design_dir: ".supernb/design/{initiative_id}"
  plan_dir: ".supernb/plans/{initiative_id}"
  release_dir: ".supernb/releases/{initiative_id}"
""".strip()
    spec_path.write_text(spec_text + "\n", encoding="utf-8")

    return {
        "project_dir": project_dir,
        "initiative_root": initiative_root,
        "spec_path": spec_path,
        "research_dir": research_dir,
        "prd_dir": prd_dir,
        "design_dir": design_dir,
        "plan_dir": plan_dir,
        "release_dir": release_dir,
        "command_briefs_dir": command_briefs_dir,
        "phase_results_dir": phase_results_dir,
        "executions_dir": executions_dir,
    }


def write_report_json(path: Path, evidence_artifacts: list[str] | None = None) -> None:
    payload = {
        "completion_status": "completed",
        "summary": "Imported execution completed.",
        "completed_items": ["Finished the requested work."],
        "remaining_items": [],
        "evidence_artifacts": evidence_artifacts or [],
        "artifacts_updated": [],
        "commands_run": ["npm test"],
        "tests_run": ["npm test"],
        "validated_batches_completed": 1,
        "batch_commits": [],
        "workflow_trace": {},
        "recommended_result_status": "succeeded",
        "recommended_gate_action": "certify",
        "recommended_gate_status": "ready",
        "follow_up": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class SupernbCliIntegrationTests(unittest.TestCase):
    def test_record_result_requires_override_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-record-result.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--status",
                "succeeded",
                "--summary",
                "Manual result",
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("--override-reason is required", proc.stderr)

    def test_import_execution_rejects_missing_evidence_before_packet_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            report_path = Path(tmp_dir) / "report.json"
            write_report_json(report_path, evidence_artifacts=["missing-proof.md"])

            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--report-json",
                str(report_path),
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("do not exist", proc.stderr)
            self.assertEqual(list(paths["executions_dir"].iterdir()), [])

    def test_import_and_apply_execution_records_packet_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            report_path = Path(tmp_dir) / "report.json"
            write_report_json(report_path)

            import_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--report-json",
                str(report_path),
            )
            self.assertEqual(import_proc.returncode, 0, msg=import_proc.stderr)

            packet_dirs = [path for path in paths["executions_dir"].iterdir() if path.is_dir()]
            self.assertEqual(len(packet_dirs), 1)

            apply_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-apply-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--packet",
                str(packet_dirs[0]),
                "--no-rerun",
            )
            self.assertEqual(apply_proc.returncode, 0, msg=apply_proc.stderr)

            result_files = list(paths["phase_results_dir"].glob("*.md"))
            self.assertEqual(len(result_files), 1)
            result_text = result_files[0].read_text(encoding="utf-8")
            self.assertIn("- Source: `execution-packet`", result_text)
            self.assertIn("- Source packet: `", result_text)

    def test_migrate_legacy_writes_mapping_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = write_spec(root)
            legacy_root = root / "legacy-supernb"
            (legacy_root / "research").mkdir(parents=True, exist_ok=True)
            (legacy_root / "implementation").mkdir(parents=True, exist_ok=True)
            (legacy_root / "misc").mkdir(parents=True, exist_ok=True)
            (legacy_root / "research" / "market-research.md").write_text("# Market research\n", encoding="utf-8")
            (legacy_root / "implementation" / "IMPLEMENTATION-PLAN.md").write_text("# Legacy plan\n", encoding="utf-8")
            (legacy_root / "misc" / "random.md").write_text("# Ignore me\n", encoding="utf-8")

            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-migrate-legacy.py"),
                "--spec",
                str(paths["spec_path"]),
                "--legacy-root",
                str(legacy_root),
                "--no-upgrade",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            mapping_md = paths["initiative_root"] / "legacy-import" / "legacy-mapping.md"
            imported_misc = paths["initiative_root"] / "legacy-import" / "misc" / "random.md"
            self.assertTrue(mapping_md.is_file())
            self.assertFalse(imported_misc.exists())
            mapping_text = mapping_md.read_text(encoding="utf-8")
            self.assertIn("01-competitor-landscape.md", mapping_text)
            self.assertIn("implementation-plan.md", mapping_text)

    def test_clean_initiative_archives_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            brief = paths["command_briefs_dir"] / "20260319-120000-product-research.md"
            brief.write_text("# Brief\n", encoding="utf-8")

            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-clean-initiative-artifacts.py"),
                "--spec",
                str(paths["spec_path"]),
                "--apply",
                "--keep-command-briefs",
                "0",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            archive_sessions = sorted((paths["initiative_root"] / "cleanup-archive").glob("session-*"))
            self.assertTrue(archive_sessions)
            manifest_md = archive_sessions[-1] / "cleanup-manifest.md"
            archived_brief = archive_sessions[-1] / "command-briefs" / brief.name
            self.assertFalse(brief.exists())
            self.assertTrue(archived_brief.is_file())
            self.assertTrue(manifest_md.is_file())


if __name__ == "__main__":
    unittest.main()
