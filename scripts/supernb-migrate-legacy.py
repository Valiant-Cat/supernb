#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.supernb_common import artifact_path as common_artifact_path, load_spec, resolve_spec_path as common_resolve_spec_path

ROOT_DIR = Path(__file__).resolve().parent.parent

LEGACY_PRIORITY_PATHS = [
    "brainstorm.md",
    "research.md",
    "research/market-research.md",
    "prd/PRD.md",
    "design/UI-UX-DESIGN.md",
    "implementation/IMPLEMENTATION-PLAN.md",
]
LEGACY_INCLUDE_EXTENSIONS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}
LEGACY_SKIP_DIRS = {
    "initiatives",
    "command-briefs",
    "phase-results",
    "executions",
    "plans",
    "releases",
    "artifacts",
    "updates",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import legacy loose .supernb project artifacts into the current initiative workspace.")
    parser.add_argument("--initiative-id", help="Existing initiative id")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--legacy-root", help="Legacy .supernb directory to inspect. Defaults to <project>/.supernb")
    parser.add_argument("--no-upgrade", action="store_true", help="Do not run upgrade-artifacts after importing legacy files")
    return parser.parse_args()


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def should_skip_relative(relative: Path) -> bool:
    return any(part in LEGACY_SKIP_DIRS for part in relative.parts)


def discover_legacy_files(legacy_root: Path) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    for raw_path in LEGACY_PRIORITY_PATHS:
        relative = Path(raw_path)
        source = legacy_root / relative
        if source.is_file() and relative not in seen:
            seen.add(relative)
            discovered.append(relative)

    for source in sorted(legacy_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(legacy_root)
        if relative in seen:
            continue
        if should_skip_relative(relative):
            continue
        if source.suffix.lower() not in LEGACY_INCLUDE_EXTENSIONS:
            continue
        seen.add(relative)
        discovered.append(relative)
    return discovered


def main() -> int:
    args = parse_args()
    try:
        spec_path = resolve_spec_path(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not spec_path.is_file():
        print(f"Initiative spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = load_spec(spec_path)
    initiative_id = str(spec.get("initiative", {}).get("id", "")).strip() or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    project_dir_value = str(spec.get("delivery", {}).get("project_dir", "")).strip()
    if not project_dir_value:
        print("delivery.project_dir is required to locate legacy project files.", file=sys.stderr)
        return 1
    project_dir = Path(project_dir_value).expanduser().resolve()
    legacy_root = Path(args.legacy_root).expanduser().resolve() if args.legacy_root else project_dir / ".supernb"
    if not legacy_root.is_dir():
        print(f"Legacy root not found: {legacy_root}", file=sys.stderr)
        return 1
    initiative_dir = artifact_path(spec, "run_status_md").parent
    legacy_import_dir = initiative_dir / "legacy-import"
    legacy_import_dir.mkdir(parents=True, exist_ok=True)

    imported: list[tuple[Path, Path]] = []
    for relative in discover_legacy_files(legacy_root):
        source = legacy_root / relative
        destination = legacy_import_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        imported.append((source, destination))

    report_path = legacy_import_dir / "legacy-import.md"
    lines = [
        "# Legacy Import",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Imported at: `{utc_now()}`",
        f"- Legacy root: `{legacy_root}`",
        "",
        "## Imported Files",
        "",
    ]
    if imported:
        for source, destination in imported:
            lines.append(f"- `{source}` -> `{destination}`")
    else:
        lines.append("- No recognized legacy files were found.")
    lines.extend(
        [
            "",
            "## Next Steps",
            "",
            f"- Review the imported legacy files under `{legacy_import_dir}`.",
            f"- Update the initiative-scoped artifacts under `{initiative_dir}` with the parts you want to preserve.",
            f"- Run `./scripts/supernb run --initiative-id {initiative_id}` after the migrated artifacts are reconciled.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if imported and not args.no_upgrade:
        subprocess.run(
            [sys.executable, str(ROOT_DIR / "scripts" / "supernb-upgrade-artifacts.py"), "--spec", str(spec_path)],
            check=True,
        )

    print(f"Initiative: {initiative_id}")
    print(f"Legacy root: {legacy_root}")
    print(f"Legacy import dir: {legacy_import_dir}")
    print(f"Import report: {report_path}")
    if imported:
        print(f"Imported files: {len(imported)}")
        if args.no_upgrade:
            print("Upgrade artifacts: skipped")
        else:
            print("Upgrade artifacts: completed")
    else:
        print("Imported files: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
