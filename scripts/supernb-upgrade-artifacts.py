#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from lib.supernb_common import artifact_path, load_spec, resolve_spec_path

ROOT_DIR = Path(__file__).resolve().parent.parent

TEMPLATE_KEYS = {
    "01-competitor-landscape.md": ROOT_DIR / "templates" / "research" / "01-competitor-landscape.md",
    "02-review-insights.md": ROOT_DIR / "templates" / "research" / "02-review-insights.md",
    "03-feature-opportunities.md": ROOT_DIR / "templates" / "research" / "03-feature-opportunities.md",
    "product-requirements.md": ROOT_DIR / "templates" / "prd" / "product-requirements.md",
    "ui-ux-spec.md": ROOT_DIR / "templates" / "design" / "ui-ux-spec.md",
    "i18n-strategy.md": ROOT_DIR / "templates" / "design" / "i18n-strategy.md",
    "implementation-plan.md": ROOT_DIR / "templates" / "plans" / "implementation-plan.md",
    "release-readiness.md": ROOT_DIR / "templates" / "releases" / "release-readiness.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append missing supernb artifact sections from the latest templates into an existing initiative.")
    parser.add_argument("--initiative-id", help="Existing initiative id")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    return parser.parse_args()


def artifact_targets(spec: dict[str, str]) -> list[Path]:
    research_dir = artifact_path(spec, "research_dir", ROOT_DIR)
    design_dir = artifact_path(spec, "design_dir", ROOT_DIR)
    prd_dir = artifact_path(spec, "prd_dir", ROOT_DIR)
    plan_dir = artifact_path(spec, "plan_dir", ROOT_DIR)
    release_dir = artifact_path(spec, "release_dir", ROOT_DIR)
    return [
        research_dir / "01-competitor-landscape.md",
        research_dir / "02-review-insights.md",
        research_dir / "03-feature-opportunities.md",
        prd_dir / "product-requirements.md",
        design_dir / "ui-ux-spec.md",
        design_dir / "i18n-strategy.md",
        plan_dir / "implementation-plan.md",
        release_dir / "release-readiness.md",
    ]


def top_level_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current is not None:
                sections[current] = current_lines[:]
            current = match.group(1).strip()
            current_lines = [line]
            continue
        if current is not None:
            current_lines.append(line)

    if current is not None:
        sections[current] = current_lines[:]
    return sections


def has_subheading(text: str, heading: str) -> bool:
    return re.search(rf"^###\s+{re.escape(heading)}\s*$", text, flags=re.MULTILINE) is not None


def append_missing_uiux_subsections(target_text: str, template_text: str) -> str:
    if has_subheading(target_text, "Page 3"):
        return target_text
    match = re.search(r"(^###\s+Page 3\s*$.*?)(?=^##\s+|\Z)", template_text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return target_text
    insertion = "\n" + match.group(1).rstrip() + "\n"
    page_specs_match = re.search(r"(^##\s+Page Specs\s*$.*?)(?=^##\s+|\Z)", target_text, flags=re.MULTILINE | re.DOTALL)
    if not page_specs_match:
        return target_text + insertion
    page_specs_block = page_specs_match.group(1).rstrip() + insertion
    return target_text[: page_specs_match.start(1)] + page_specs_block + target_text[page_specs_match.end(1) :]


def append_missing_plan_subsections(target_text: str, template_text: str) -> str:
    if has_subheading(target_text, "Batch 3"):
        return target_text
    match = re.search(r"(^###\s+Batch 3\s*$.*?)(?=^##\s+|\Z)", template_text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return target_text
    insertion = "\n" + match.group(1).rstrip() + "\n"
    task_batches_match = re.search(r"(^##\s+Task Batches\s*$.*?)(?=^##\s+|\Z)", target_text, flags=re.MULTILINE | re.DOTALL)
    if not task_batches_match:
        return target_text + insertion
    task_batches_block = task_batches_match.group(1).rstrip() + insertion
    return target_text[: task_batches_match.start(1)] + task_batches_block + target_text[task_batches_match.end(1) :]


def upgrade_file(target_path: Path, template_path: Path) -> bool:
    if not target_path.is_file() or not template_path.is_file():
        return False

    target_text = target_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")
    target_sections = top_level_sections(target_text)
    template_sections = top_level_sections(template_text)

    appended_blocks: list[str] = []
    for name, block_lines in template_sections.items():
        if name in target_sections:
            continue
        appended_blocks.append("\n".join(block_lines).rstrip())

    updated_text = target_text.rstrip() + ("\n\n" + "\n\n".join(appended_blocks) if appended_blocks else "")

    if target_path.name == "ui-ux-spec.md":
        updated_text = append_missing_uiux_subsections(updated_text, template_text)
    if target_path.name == "implementation-plan.md":
        updated_text = append_missing_plan_subsections(updated_text, template_text)

    updated_text = updated_text.rstrip() + "\n"
    if updated_text == target_text:
        return False

    target_path.write_text(updated_text, encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    try:
        spec_path = resolve_spec_path(args, ROOT_DIR)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not spec_path.is_file():
        print(f"Initiative spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = load_spec(spec_path)
    changed: list[Path] = []
    for target in artifact_targets(spec):
        template = TEMPLATE_KEYS.get(target.name)
        if template and upgrade_file(target, template):
            changed.append(target)

    if changed:
        print("Upgraded artifact files:")
        for path in changed:
            print(path)
    else:
        print("No artifact files needed section upgrades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
