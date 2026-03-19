#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
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
LEGACY_INTEREST_DIRS = {"research", "prd", "design", "implementation", "release"}
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


def is_priority_relative(relative: Path) -> bool:
    return relative.as_posix() in LEGACY_PRIORITY_PATHS


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
        if not is_priority_relative(relative):
            if not relative.parts:
                continue
            if len(relative.parts) == 1:
                continue
            if relative.parts[0] not in LEGACY_INTEREST_DIRS:
                continue
        seen.add(relative)
        discovered.append(relative)
    return discovered


def suggest_target(spec: dict[str, Any], relative: Path) -> tuple[str, str, str]:
    relative_text = relative.as_posix().lower()
    if relative_text == "brainstorm.md":
        return (
            str(artifact_path(spec, "research_dir") / "03-feature-opportunities.md"),
            "medium",
            "Merge distilled opportunity themes and unmet-need notes into feature opportunities.",
        )
    if relative_text in {"research.md", "research/market-research.md"}:
        return (
            str(artifact_path(spec, "research_dir") / "01-competitor-landscape.md"),
            "high",
            "Merge competitor coverage, metadata, monetization, and market observations into the research landscape artifact.",
        )
    if relative_text.startswith("research/"):
        if "review" in relative_text or "insight" in relative_text:
            target = artifact_path(spec, "research_dir") / "02-review-insights.md"
            rationale = "Merge review-mining findings into the review insights artifact."
        elif "feature" in relative_text or "opportun" in relative_text:
            target = artifact_path(spec, "research_dir") / "03-feature-opportunities.md"
            rationale = "Merge opportunity framing into the feature opportunities artifact."
        else:
            target = artifact_path(spec, "research_dir") / "01-competitor-landscape.md"
            rationale = "Merge broader market and competitor notes into the research landscape artifact."
        return str(target), "medium", rationale
    if relative_text.startswith("prd/"):
        return (
            str(artifact_path(spec, "prd_dir") / "product-requirements.md"),
            "high",
            "Merge legacy PRD content into the initiative-scoped product requirements document.",
        )
    if relative_text.startswith("design/"):
        return (
            str(artifact_path(spec, "design_dir") / "ui-ux-spec.md"),
            "high",
            "Merge UI/UX specifications into the initiative-scoped design spec.",
        )
    if relative_text.startswith("implementation/"):
        return (
            str(artifact_path(spec, "plan_dir") / "implementation-plan.md"),
            "high",
            "Merge delivery sequencing, batches, and verification details into the current implementation plan.",
        )
    if relative_text.startswith("release/"):
        return (
            str(artifact_path(spec, "release_dir") / "release-readiness.md"),
            "high",
            "Merge release checks, rollout, and watchlist detail into the release readiness artifact.",
        )
    return ("manual-review", "low", "Review manually and merge only if the content materially strengthens the current initiative artifacts.")


def write_mapping_reports(
    mapping_md_path: Path,
    mapping_json_path: Path,
    initiative_id: str,
    legacy_root: Path,
    mapping_rows: list[dict[str, str]],
) -> None:
    lines = [
        "# Legacy Mapping Suggestions",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Generated at: `{utc_now()}`",
        f"- Legacy root: `{legacy_root}`",
        "",
        "## Suggested Mappings",
        "",
    ]
    if mapping_rows:
        for row in mapping_rows:
            lines.extend(
                [
                    f"### `{row['relative_path']}`",
                    "",
                    f"- Imported copy: `{row['imported_copy']}`",
                    f"- Suggested target: `{row['suggested_target']}`",
                    f"- Confidence: `{row['confidence']}`",
                    f"- Rationale: {row['rationale']}",
                    "",
                ]
            )
    else:
        lines.append("- No legacy files were imported, so no mapping suggestions were generated.")
    mapping_md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    mapping_json_path.write_text(json.dumps({"initiative_id": initiative_id, "generated_at": utc_now(), "mappings": mapping_rows}, indent=2) + "\n", encoding="utf-8")


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
    mapping_md_path = legacy_import_dir / "legacy-mapping.md"
    mapping_json_path = legacy_import_dir / "legacy-mapping.json"

    imported: list[tuple[Path, Path]] = []
    mapping_rows: list[dict[str, str]] = []
    for relative in discover_legacy_files(legacy_root):
        source = legacy_root / relative
        destination = legacy_import_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        imported.append((source, destination))
        suggested_target, confidence, rationale = suggest_target(spec, relative)
        mapping_rows.append(
            {
                "relative_path": relative.as_posix(),
                "source_path": str(source),
                "imported_copy": str(destination),
                "suggested_target": suggested_target,
                "confidence": confidence,
                "rationale": rationale,
            }
        )

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
            "## Mapping Suggestions",
            "",
            f"- Mapping report: `{mapping_md_path}`",
            f"- Mapping data: `{mapping_json_path}`",
            "",
            "## Next Steps",
            "",
            f"- Review the imported legacy files under `{legacy_import_dir}`.",
            f"- Start with the suggested targets in `{mapping_md_path}` instead of reconciling files ad hoc.",
            f"- Update the initiative-scoped artifacts under `{initiative_dir}` with the parts you want to preserve.",
            f"- Run `./scripts/supernb run --initiative-id {initiative_id}` after the migrated artifacts are reconciled.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_mapping_reports(mapping_md_path, mapping_json_path, initiative_id, legacy_root, mapping_rows)

    if imported and not args.no_upgrade:
        subprocess.run(
            [sys.executable, str(ROOT_DIR / "scripts" / "supernb-upgrade-artifacts.py"), "--spec", str(spec_path)],
            check=True,
        )

    print(f"Initiative: {initiative_id}")
    print(f"Legacy root: {legacy_root}")
    print(f"Legacy import dir: {legacy_import_dir}")
    print(f"Import report: {report_path}")
    print(f"Mapping report: {mapping_md_path}")
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
