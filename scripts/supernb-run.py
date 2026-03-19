#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
PHASES = ["research", "prd", "design", "planning", "delivery", "release"]


@dataclass
class PhaseResult:
    name: str
    status: str
    blockers: list[str]
    evidence: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute initiative gates and generate the next supernb command.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", choices=["auto", *PHASES], default="auto", help="Phase to inspect")
    parser.add_argument("--no-next-command", action="store_true", help="Do not render next-command.md")
    return parser.parse_args()


def try_load_pyyaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    return yaml.safe_load(text)


def parse_scalar(value: str) -> Any:
    if value in {'""', "''"}:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        inner = value[1:-1]
        return bytes(inner, "utf-8").decode("unicode_escape")
    lower = value.lower()
    if lower in {"true", "yes"}:
        return True
    if lower in {"false", "no"}:
        return False
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            raise ValueError(f"Unsupported YAML list syntax at line {lineno}: {raw_line}")
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"Unsupported indentation at line {lineno}: {raw_line}")
        if ":" not in stripped:
            raise ValueError(f"Expected key/value pair at line {lineno}: {raw_line}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if value == "":
            child: dict[str, Any] = {}
            container[key] = child
            stack.append((indent, child))
        else:
            container[key] = parse_scalar(value)

    return root


def load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    loaded = try_load_pyyaml(text)
    if loaded is not None:
        return loaded
    return parse_simple_yaml(text)


def nested_get(data: dict[str, Any], *keys: str, default: str = "") -> str:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    if current is None:
        return default
    if isinstance(current, bool):
        return "yes" if current else "no"
    value = str(current).strip()
    if re.fullmatch(r"\{\{[^}]+\}\}", value):
        return default
    return value


def read_markdown_field(path: Path, field_name: str) -> str:
    if not path.is_file():
        return ""
    pattern = re.compile(r"^- ([^:]+):\s*(.*)$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        key = match.group(1).strip().lower()
        value = match.group(2).strip().strip("`")
        if key == field_name.lower():
            return value
    return ""


def normalize(value: str) -> str:
    return value.strip().lower()


def is_complete_status(value: str) -> bool:
    return normalize(value) in {"approved", "complete", "completed", "done"}


def is_truthy_status(value: str) -> bool:
    return normalize(value) in {"yes", "true", "ready", "approved", "complete", "completed"}


def is_delivery_complete(value: str) -> bool:
    return normalize(value) in {"verified", "complete", "completed", "done"}


def is_release_ready(value: str) -> bool:
    return normalize(value) in {"ready", "approved", "ship-ready", "shipped", "released"}


def spec_missing(spec: dict[str, Any], field_map: list[tuple[tuple[str, ...], str]]) -> list[str]:
    missing: list[str] = []
    for path_keys, label in field_map:
        if not nested_get(spec, *path_keys):
            missing.append(label)
    return missing


def build_phase_results(spec: dict[str, Any], spec_path: Path) -> tuple[dict[str, PhaseResult], dict[str, str]]:
    artifacts = {
        "research_dir": ROOT_DIR / nested_get(spec, "artifacts", "research_dir"),
        "prd_dir": ROOT_DIR / nested_get(spec, "artifacts", "prd_dir"),
        "design_dir": ROOT_DIR / nested_get(spec, "artifacts", "design_dir"),
        "plan_dir": ROOT_DIR / nested_get(spec, "artifacts", "plan_dir"),
        "release_dir": ROOT_DIR / nested_get(spec, "artifacts", "release_dir"),
    }

    research_files = [
        artifacts["research_dir"] / "01-competitor-landscape.md",
        artifacts["research_dir"] / "02-review-insights.md",
        artifacts["research_dir"] / "03-feature-opportunities.md",
    ]
    prd_file = artifacts["prd_dir"] / "product-requirements.md"
    ui_spec_file = artifacts["design_dir"] / "ui-ux-spec.md"
    i18n_file = artifacts["design_dir"] / "i18n-strategy.md"
    plan_file = artifacts["plan_dir"] / "implementation-plan.md"
    release_file = artifacts["release_dir"] / "release-readiness.md"

    research_doc_statuses = [read_markdown_field(path, "Status") for path in research_files]
    prd_status = read_markdown_field(prd_file, "Approval status")
    ui_status = read_markdown_field(ui_spec_file, "Approval status")
    i18n_status = read_markdown_field(i18n_file, "Approval status")
    plan_ready = read_markdown_field(plan_file, "Ready for execution")
    delivery_status = read_markdown_field(plan_file, "Delivery status")
    release_status = read_markdown_field(release_file, "Release decision")

    research_complete = all(is_complete_status(status) for status in research_doc_statuses if status) and all(status for status in research_doc_statuses)
    prd_complete = is_complete_status(prd_status)
    design_complete = is_complete_status(ui_status) and is_complete_status(i18n_status)
    planning_complete = is_truthy_status(plan_ready)
    delivery_complete = is_delivery_complete(delivery_status)
    release_complete = is_release_ready(release_status)

    spec_fields = {
        "research": spec_missing(
            spec,
            [
                (("delivery", "goal"), "delivery.goal"),
                (("delivery", "product_category"), "delivery.product_category"),
                (("delivery", "markets"), "delivery.markets"),
                (("delivery", "research_window"), "delivery.research_window"),
            ],
        ),
        "design": spec_missing(
            spec,
            [
                (("delivery", "goal"), "delivery.goal"),
                (("delivery", "platform"), "delivery.platform"),
                (("delivery", "source_locale"), "delivery.source_locale"),
            ],
        ),
        "planning": spec_missing(
            spec,
            [
                (("delivery", "repository"), "delivery.repository"),
                (("delivery", "stack"), "delivery.stack"),
                (("delivery", "quality_bar"), "delivery.quality_bar"),
            ],
        ),
    }

    results: dict[str, PhaseResult] = {}

    research_blockers = [f"Fill {name} in {spec_path}" for name in spec_fields["research"]]
    results["research"] = PhaseResult(
        name="research",
        status="complete" if research_complete else ("blocked" if research_blockers else "ready"),
        blockers=research_blockers,
        evidence=[
            f"competitor landscape status: {research_doc_statuses[0] or 'missing'}",
            f"review insights status: {research_doc_statuses[1] or 'missing'}",
            f"feature opportunities status: {research_doc_statuses[2] or 'missing'}",
        ],
    )

    prd_blockers = []
    if not research_complete:
        prd_blockers.append("Research phase is not approved yet.")
    results["prd"] = PhaseResult(
        name="prd",
        status="complete" if research_complete and prd_complete else ("blocked" if prd_blockers else "ready"),
        blockers=prd_blockers,
        evidence=[f"prd approval status: {prd_status or 'missing'}"],
    )

    design_blockers = []
    if not prd_complete:
        design_blockers.append("PRD is not approved yet.")
    design_blockers.extend(f"Fill {name} in {spec_path}" for name in spec_fields["design"])
    results["design"] = PhaseResult(
        name="design",
        status="complete" if prd_complete and design_complete else ("blocked" if design_blockers else "ready"),
        blockers=design_blockers,
        evidence=[
            f"ui ux spec approval status: {ui_status or 'missing'}",
            f"i18n strategy approval status: {i18n_status or 'missing'}",
        ],
    )

    planning_blockers = []
    if not design_complete:
        planning_blockers.append("Design phase is not approved yet.")
    planning_blockers.extend(f"Fill {name} in {spec_path}" for name in spec_fields["planning"])
    results["planning"] = PhaseResult(
        name="planning",
        status="complete" if design_complete and planning_complete else ("blocked" if planning_blockers else "ready"),
        blockers=planning_blockers,
        evidence=[f"implementation plan ready for execution: {plan_ready or 'missing'}"],
    )

    delivery_blockers = []
    if not planning_complete:
        delivery_blockers.append("Implementation plan is not marked ready for execution yet.")
    results["delivery"] = PhaseResult(
        name="delivery",
        status="complete" if planning_complete and delivery_complete else ("blocked" if delivery_blockers else "ready"),
        blockers=delivery_blockers,
        evidence=[f"delivery status: {delivery_status or 'missing'}"],
    )

    release_blockers = []
    if not delivery_complete:
        release_blockers.append("Delivery phase is not verified yet.")
    results["release"] = PhaseResult(
        name="release",
        status="complete" if delivery_complete and release_complete else ("blocked" if release_blockers else "ready"),
        blockers=release_blockers,
        evidence=[f"release decision: {release_status or 'missing'}"],
    )

    meta = {
        "research_complete": "yes" if research_complete else "no",
        "prd_complete": "yes" if prd_complete else "no",
        "design_complete": "yes" if design_complete else "no",
        "planning_complete": "yes" if planning_complete else "no",
        "delivery_complete": "yes" if delivery_complete else "no",
        "release_complete": "yes" if release_complete else "no",
    }
    return results, meta


def auto_phase(results: dict[str, PhaseResult]) -> str:
    for phase in PHASES:
        if results[phase].status != "complete":
            return phase
    return "release"


def command_for_phase(phase: str) -> tuple[str, str, str]:
    if phase in {"research", "prd"}:
        return ("product-research-prd", "Produce approved research and a cited PRD", "")
    if phase == "design":
        return ("ui-ux-governance", "Produce approved UI/UX and i18n design artifacts", "")
    if phase in {"planning", "delivery"}:
        return ("autonomous-delivery", "Deliver the approved scope in validated batches", "")
    return ("supernb-orchestrator", "Run final verification and release readiness checks", "release-readiness + verification-before-completion + ui audit")


def render_next_command(spec: dict[str, Any], phase: str, output_path: Path) -> dict[str, str] | None:
    command_name, default_goal, capability_hint = command_for_phase(phase)
    constraints = nested_get(spec, "delivery", "constraints")
    quality_bar = nested_get(spec, "delivery", "quality_bar")
    if quality_bar:
        constraints = f"{constraints}; quality bar: {quality_bar}" if constraints else f"quality bar: {quality_bar}"

    args = [
        str(ROOT_DIR / "scripts" / "render-command.sh"),
        "--command",
        command_name,
        "--goal",
        nested_get(spec, "delivery", "goal") or default_goal,
        "--repository",
        nested_get(spec, "delivery", "repository"),
        "--platform",
        nested_get(spec, "delivery", "platform"),
        "--stack",
        nested_get(spec, "delivery", "stack"),
        "--markets",
        nested_get(spec, "delivery", "markets"),
        "--constraints",
        constraints,
        "--initiative-id",
        nested_get(spec, "initiative", "id"),
        "--output-file",
        str(output_path),
    ]

    if command_name in {"product-research-prd", "full-product-delivery"}:
        args.extend(
            [
                "--product-category",
                nested_get(spec, "delivery", "product_category"),
                "--seed-competitors",
                nested_get(spec, "delivery", "seed_competitors"),
                "--research-window",
                nested_get(spec, "delivery", "research_window"),
            ]
        )
    if command_name == "supernb-orchestrator" and capability_hint:
        args.extend(["--capability-hint", capability_hint])
    if command_name == "ui-ux-governance":
        args.extend(["--context-line", f"source locale: {nested_get(spec, 'delivery', 'source_locale') or '<fill source locale>'}"])
        args.extend(["--context-line", f"target locales: {nested_get(spec, 'delivery', 'target_locales') or '<fill target locales>'}"])

    subprocess.run(args, check=True)
    return {"command": command_name, "path": str(output_path.relative_to(ROOT_DIR))}


def build_markdown(
    spec: dict[str, Any],
    spec_path: Path,
    selected_phase: str,
    results: dict[str, PhaseResult],
    meta: dict[str, str],
    next_command: dict[str, str] | None,
) -> str:
    title = nested_get(spec, "initiative", "title")
    initiative_id = nested_get(spec, "initiative", "id")
    lines = [
        f"# Run Status: {title or initiative_id}",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Generated: `{utc_now()}`",
        f"- Initiative spec: `{spec_path.relative_to(ROOT_DIR)}`",
        f"- Selected phase: `{selected_phase}`",
        "",
        "## Completion Snapshot",
        "",
        f"- Research complete: `{meta['research_complete']}`",
        f"- PRD complete: `{meta['prd_complete']}`",
        f"- Design complete: `{meta['design_complete']}`",
        f"- Planning complete: `{meta['planning_complete']}`",
        f"- Delivery complete: `{meta['delivery_complete']}`",
        f"- Release complete: `{meta['release_complete']}`",
        "",
        "## Phase Summary",
        "",
        "| Phase | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for phase in PHASES:
        evidence = "; ".join(results[phase].evidence)
        lines.append(f"| {phase} | {results[phase].status} | {evidence} |")

    current = results[selected_phase]
    lines.extend(["", f"## Current Phase: {selected_phase}", ""])
    if current.blockers:
        lines.append("### Blockers")
        lines.append("")
        for blocker in current.blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- No blocking gate found for the selected phase.")

    lines.extend(["", "## Next Action", ""])
    if next_command is None:
        lines.append("- No command brief was generated because the selected phase is blocked by missing spec fields or unmet gates.")
    else:
        lines.append(f"- Command: `{next_command['command']}`")
        lines.append(f"- Rendered brief: `{next_command['path']}`")
        lines.append(f"- Run: `./scripts/supernb run --initiative-id {initiative_id}` after phase progress changes")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()

    if not args.initiative_id and not args.spec:
        print("Pass --initiative-id or --spec.", file=sys.stderr)
        return 1

    if args.spec:
        spec_path = Path(args.spec).expanduser().resolve()
    else:
        spec_path = ROOT_DIR / "artifacts" / "initiatives" / args.initiative_id / "initiative.yaml"

    if not spec_path.is_file():
        print(f"Initiative spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = load_spec(spec_path)
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    results, meta = build_phase_results(spec, spec_path)
    selected_phase = args.phase if args.phase != "auto" else auto_phase(results)

    run_status_md = ROOT_DIR / nested_get(spec, "artifacts", "run_status_md")
    run_status_json = ROOT_DIR / nested_get(spec, "artifacts", "run_status_json")
    next_command_md = ROOT_DIR / nested_get(spec, "artifacts", "next_command_md")
    run_status_md.parent.mkdir(parents=True, exist_ok=True)

    next_command = None
    if not args.no_next_command and results[selected_phase].status != "blocked":
        next_command = render_next_command(spec, selected_phase, next_command_md)

    markdown = build_markdown(spec, spec_path, selected_phase, results, meta, next_command)
    run_status_md.write_text(markdown, encoding="utf-8")

    payload = {
        "initiative_id": initiative_id,
        "selected_phase": selected_phase,
        "generated_at": utc_now(),
        "spec_path": str(spec_path.relative_to(ROOT_DIR)),
        "phases": {
            phase: {
                "status": results[phase].status,
                "blockers": results[phase].blockers,
                "evidence": results[phase].evidence,
            }
            for phase in PHASES
        },
        "next_command": next_command,
    }
    run_status_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Initiative: {initiative_id}")
    print(f"Selected phase: {selected_phase} ({results[selected_phase].status})")
    print(f"Run status: {run_status_md}")
    print(f"Run status JSON: {run_status_json}")
    if next_command:
        print(f"Next command: {next_command_md}")
    else:
        print("Next command: not generated because the selected phase is blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
