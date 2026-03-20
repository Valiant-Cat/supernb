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
        proc = subprocess.run(command, cwd=project_dir)
        return proc.returncode

    specs = discover_initiative_specs(project_dir)
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
