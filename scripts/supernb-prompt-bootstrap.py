#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lib.supernb_common import artifact_path as common_artifact_path
from lib.supernb_common import load_json_file
from lib.supernb_common import load_spec
from lib.supernb_common import markdown_field
from lib.supernb_common import reassessment_indicates_next_development_cycle
from lib.supernb_common import run_status_indicates_completed_cycle

ROOT_DIR = Path(__file__).resolve().parent.parent
INIT_SCRIPT = ROOT_DIR / "scripts" / "init-initiative.sh"
PROMPT_SYNC_SCRIPT = ROOT_DIR / "scripts" / "supernb-prompt-sync.py"
MIGRATE_LEGACY_SCRIPT = ROOT_DIR / "scripts" / "supernb-migrate-legacy.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single-entry prompt-first bootstrap for Claude Code. Auto-discovers or initializes the current project initiative, optionally migrates legacy .supernb content, then runs prompt-sync."
    )
    parser.add_argument("--initiative-id", help="Existing initiative id to bootstrap directly.")
    parser.add_argument("--spec", help="Explicit initiative.yaml path.")
    parser.add_argument("--project-dir", help="Project root. Defaults to the current working directory.")
    parser.add_argument("--phase", choices=["auto", "research", "prd", "design", "planning", "delivery", "release"], default="auto")
    parser.add_argument("--title", help="Title for an auto-created initiative. Defaults to the current directory name.")
    parser.add_argument("--initiative-slug", help="Slug for an auto-created initiative. Defaults to the current directory name.")
    parser.add_argument("--goal", help="Optional goal written into an auto-created initiative.")
    parser.add_argument("--no-run", action="store_true", help="Forward --no-run to prompt-sync.")
    parser.add_argument("--start-loop", action="store_true", help="Forward --start-loop to prompt-sync.")
    parser.add_argument(
        "--direct-bridge-fallback",
        action="store_true",
        help="Forward --direct-bridge-fallback to prompt-sync so loop-required phases can auto-switch to direct Claude bridging.",
    )
    parser.add_argument("--no-auto-init", action="store_true", help="Fail instead of auto-initializing when no initiative exists in the current project.")
    return parser.parse_args()


def project_dir_from_args(args: argparse.Namespace) -> Path:
    return Path(args.project_dir).expanduser().resolve() if args.project_dir else Path.cwd().resolve()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "project"


def discover_initiative_specs(project_dir: Path) -> list[Path]:
    initiatives_root = project_dir / ".supernb" / "initiatives"
    if not initiatives_root.is_dir():
        return []
    candidates = sorted(initiatives_root.glob("*/initiative.yaml"))
    if not candidates:
        return []

    def sort_key(path: Path) -> tuple[float, str]:
        run_status = path.parent / "run-status.json"
        timestamp = run_status.stat().st_mtime if run_status.exists() else path.stat().st_mtime
        return (timestamp, str(path))

    return sorted((path.resolve() for path in candidates), key=sort_key, reverse=True)


def normalize(value: str) -> str:
    return value.strip().lower()


def initiative_should_roll_into_follow_on(spec_path: Path) -> bool:
    spec = load_spec(spec_path)
    plan_file = common_artifact_path(spec, "plan_dir", ROOT_DIR) / "implementation-plan.md"
    release_file = common_artifact_path(spec, "release_dir", ROOT_DIR) / "release-readiness.md"
    delivery_status = normalize(markdown_field(plan_file, "Delivery status"))
    release_status = normalize(markdown_field(release_file, "Release decision"))
    legacy_release_ready = delivery_status in {"verified", "complete", "completed", "done"} and release_status in {
        "ready",
        "approved",
        "ship-ready",
        "shipped",
        "released",
    }
    initiative_root = spec_path.parent
    run_status_complete = run_status_indicates_completed_cycle(initiative_root / "run-status.json")
    reassessment_next_cycle = reassessment_indicates_next_development_cycle(initiative_root / "initiative-reassessment.md")
    certification_state = load_json_file(initiative_root / "certification-state.json")
    phases = certification_state.get("phases", {}) if isinstance(certification_state.get("phases"), dict) else {}
    delivery_cert = phases.get("delivery", {}) if isinstance(phases.get("delivery"), dict) else {}
    release_cert = phases.get("release", {}) if isinstance(phases.get("release"), dict) else {}
    certified_cycle_complete = (
        bool(delivery_cert.get("passed"))
        and bool(release_cert.get("passed"))
        and normalize(str(release_cert.get("recommended_gate_status", ""))) == "ready"
    )
    return legacy_release_ready or run_status_complete or (reassessment_next_cycle and certified_cycle_complete)


def legacy_workspace_present(project_dir: Path) -> bool:
    legacy_root = project_dir / ".supernb"
    if not legacy_root.is_dir():
        return False
    if any((legacy_root / "initiatives").glob("*/initiative.yaml")):
        return False
    interesting = ["research", "prd", "design", "implementation", "release", "brainstorm.md", "research.md"]
    return any((legacy_root / item).exists() for item in interesting)


def snapshot_legacy_root(project_dir: Path) -> Path | None:
    legacy_root = project_dir / ".supernb"
    if not legacy_workspace_present(project_dir):
        return None
    temp_root = Path(tempfile.mkdtemp(prefix="supernb-legacy-"))
    snapshot = temp_root / "legacy-supernb"
    shutil.copytree(legacy_root, snapshot)
    return snapshot


def init_new_initiative(project_dir: Path, args: argparse.Namespace) -> Path:
    if project_dir == Path.home():
        raise RuntimeError("Refusing to auto-initialize an initiative in the home directory. Open the target project directory first.")
    if not INIT_SCRIPT.is_file():
        raise FileNotFoundError(f"init-initiative script not found: {INIT_SCRIPT}")

    title = (args.title or project_dir.name).strip() or "Project"
    slug = slugify(args.initiative_slug or project_dir.name)
    goal = (args.goal or f"Refine, deepen, and upgrade the current product in {project_dir.name} to a 10M-DAU-grade quality bar.").strip()

    env = os.environ.copy()
    env.update(
        {
            "PROJECT_DIR": str(project_dir),
            "REPOSITORY": str(project_dir if (project_dir / ".git").exists() else ""),
            "HARNESS": "claude-code",
            "GOAL": goal,
        }
    )
    proc = subprocess.run(
        [str(INIT_SCRIPT), slug, title],
        cwd=project_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip() or "init-initiative failed"
        raise RuntimeError(stderr)

    specs = discover_initiative_specs(project_dir)
    if not specs:
        raise RuntimeError("init-initiative completed but no initiative.yaml was created.")
    return specs[0]


def migrate_legacy_if_needed(spec_path: Path, legacy_snapshot: Path | None) -> None:
    if legacy_snapshot is None:
        return
    proc = subprocess.run(
        [sys.executable, str(MIGRATE_LEGACY_SCRIPT), "--spec", str(spec_path), "--legacy-root", str(legacy_snapshot)],
        cwd=spec_path.parent.parent.parent.parent,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip() or "migrate-legacy failed"
        raise RuntimeError(stderr)


def prompt_sync(spec_path: Path, args: argparse.Namespace) -> int:
    command = [sys.executable, str(PROMPT_SYNC_SCRIPT), "--spec", str(spec_path)]
    if args.phase != "auto":
        command.extend(["--phase", args.phase])
    if args.no_run:
        command.append("--no-run")
    if args.start_loop:
        command.append("--start-loop")
    if args.direct_bridge_fallback:
        command.append("--direct-bridge-fallback")

    proc = subprocess.run(command, cwd=project_dir_from_args(args))
    return proc.returncode


def main() -> int:
    args = parse_args()
    project_dir = project_dir_from_args(args)

    if args.spec:
        spec_path = Path(args.spec).expanduser().resolve()
        return prompt_sync(spec_path, args)

    if args.initiative_id:
        command = [sys.executable, str(PROMPT_SYNC_SCRIPT), "--initiative-id", args.initiative_id]
        if args.phase != "auto":
            command.extend(["--phase", args.phase])
        if args.no_run:
            command.append("--no-run")
        if args.start_loop:
            command.append("--start-loop")
        if args.direct_bridge_fallback:
            command.append("--direct-bridge-fallback")
        proc = subprocess.run(command, cwd=project_dir)
        return proc.returncode

    specs = discover_initiative_specs(project_dir)
    if specs:
        if args.phase == "auto" and initiative_should_roll_into_follow_on(specs[0]):
            print(
                f"Existing initiative `{specs[0].parent.name}` has already reached a release-ready cycle; "
                "starting a new follow-on initiative for continued product upgrades."
            )
        else:
            return prompt_sync(specs[0], args)

    if specs and args.phase == "auto":
        legacy_snapshot = snapshot_legacy_root(project_dir)
        try:
            spec_path = init_new_initiative(project_dir, args)
            migrate_legacy_if_needed(spec_path, legacy_snapshot)
            return prompt_sync(spec_path, args)
        finally:
            if legacy_snapshot is not None:
                shutil.rmtree(legacy_snapshot.parent, ignore_errors=True)

    if specs:
        return prompt_sync(specs[0], args)

    if args.no_auto_init:
        print(
            f"No initiative.yaml found under {project_dir / '.supernb' / 'initiatives'}. "
            "Initialize an initiative first or rerun without --no-auto-init.",
            file=sys.stderr,
        )
        return 1

    legacy_snapshot = snapshot_legacy_root(project_dir)
    try:
        spec_path = init_new_initiative(project_dir, args)
        migrate_legacy_if_needed(spec_path, legacy_snapshot)
        return prompt_sync(spec_path, args)
    finally:
        if legacy_snapshot is not None:
            shutil.rmtree(legacy_snapshot.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
