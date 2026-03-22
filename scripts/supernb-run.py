#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.supernb_common import (
    PHASES,
    append_debug_log as common_append_debug_log,
    artifact_path as common_artifact_path,
    certification_passed,
    certification_snapshot_matches,
    certification_state_path as common_certification_state_path,
    display_path as common_display_path,
    load_certification_state,
    load_spec,
    nested_get,
    phase_has_recorded_activity,
    phase_artifact_snapshot,
    phase_targets,
    prompt_first_retry_blocker,
    project_root as common_project_root,
    resolve_spec_path as common_resolve_spec_path,
    supernb_cli_prefix,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]
EXPECTED_GATE_STATUS = {
    "research": "approved",
    "prd": "approved",
    "design": "approved",
    "planning": "ready",
    "delivery": "verified",
    "release": "ready",
}
_EXECUTE_NEXT_MODULE: Any | None = None


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

def display_path(path: Path) -> str:
    return common_display_path(path, DISPLAY_ROOTS)


def project_root(spec: dict[str, Any]) -> Path:
    return common_project_root(spec, ROOT_DIR)


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def certification_state_path(spec: dict[str, Any]) -> Path:
    return common_certification_state_path(spec, ROOT_DIR)


def debug_log(spec: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    common_append_debug_log(spec, ROOT_DIR, "supernb-run", event, payload)


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


def certification_entry(spec: dict[str, Any], phase: str) -> dict[str, Any]:
    state = load_certification_state(certification_state_path(spec))
    phases = state.get("phases")
    if not isinstance(phases, dict):
        return {}
    entry = phases.get(phase)
    return entry if isinstance(entry, dict) else {}


def certification_evidence(spec: dict[str, Any], phase: str) -> str:
    entry = certification_entry(spec, phase)
    current_snapshot = phase_artifact_snapshot(spec, phase, ROOT_DIR, DISPLAY_ROOTS)
    if certification_passed(entry, EXPECTED_GATE_STATUS[phase]) and certification_snapshot_matches(entry, current_snapshot):
        report_path = str(entry.get("report_path", "")).strip()
        if report_path:
            return f"certification: passed ({report_path})"
        return "certification: passed"
    if certification_passed(entry, EXPECTED_GATE_STATUS[phase]) and not certification_snapshot_matches(entry, current_snapshot):
        return "certification: stale (artifacts changed since certification)"
    if entry:
        return f"certification: pending or failed (last checked {entry.get('checked_at', 'unknown')})"
    return "certification: not recorded"


def certification_notice(spec: dict[str, Any], phase: str) -> str:
    entry = certification_entry(spec, phase)
    if not entry:
        return ""
    current_snapshot = phase_artifact_snapshot(spec, phase, ROOT_DIR, DISPLAY_ROOTS)
    expected_status = EXPECTED_GATE_STATUS[phase]
    report_path = str(entry.get("report_path", "")).strip()
    report_suffix = f" Latest certification report: {report_path}." if report_path else ""
    if certification_passed(entry, expected_status) and certification_snapshot_matches(entry, current_snapshot):
        return ""
    if certification_passed(entry, expected_status) and not certification_snapshot_matches(entry, current_snapshot):
        return f"Latest {phase} certification is stale because artifacts changed since the last passing certification.{report_suffix}"
    return f"Latest {phase} certification has not passed yet.{report_suffix}"


def load_execute_next_module() -> Any:
    global _EXECUTE_NEXT_MODULE
    if _EXECUTE_NEXT_MODULE is not None:
        return _EXECUTE_NEXT_MODULE

    module_path = ROOT_DIR / "scripts" / "supernb-execute-next.py"
    module_spec = importlib.util.spec_from_file_location("supernb_execute_next", module_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load execute-next module from {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    _EXECUTE_NEXT_MODULE = module
    return module


def build_phase_readiness(spec: dict[str, Any], phase: str) -> dict[str, Any]:
    module = load_execute_next_module()
    return module.build_phase_readiness(spec, phase)


def should_surface_readiness_blocker(phase: str, artifact_exists: bool, gate_field: str, cert_entry: dict[str, Any]) -> bool:
    if phase not in {"planning", "delivery", "release"}:
        return False
    return artifact_exists or bool(gate_field) or bool(cert_entry)


def phase_incomplete_blockers(spec: dict[str, Any], phase: str, complete: bool) -> list[str]:
    if complete:
        return []
    notice = certification_notice(spec, phase)
    return [notice] if notice else []


def build_phase_results(spec: dict[str, Any], spec_path: Path) -> tuple[dict[str, PhaseResult], dict[str, str]]:
    artifacts = {
        "research_dir": artifact_path(spec, "research_dir"),
        "prd_dir": artifact_path(spec, "prd_dir"),
        "design_dir": artifact_path(spec, "design_dir"),
        "plan_dir": artifact_path(spec, "plan_dir"),
        "release_dir": artifact_path(spec, "release_dir"),
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

    research_status_complete = all(is_complete_status(status) for status in research_doc_statuses if status) and all(status for status in research_doc_statuses)
    prd_status_complete = is_complete_status(prd_status)
    design_status_complete = is_complete_status(ui_status) and is_complete_status(i18n_status)
    planning_status_complete = is_truthy_status(plan_ready)
    delivery_status_complete = is_delivery_complete(delivery_status)
    release_status_complete = is_release_ready(release_status)

    planning_cert_entry = certification_entry(spec, "planning")
    delivery_cert_entry = certification_entry(spec, "delivery")
    release_cert_entry = certification_entry(spec, "release")
    planning_readiness = build_phase_readiness(spec, "planning")
    delivery_readiness = build_phase_readiness(spec, "delivery")
    release_readiness = build_phase_readiness(spec, "release")

    research_complete = research_status_complete and certification_passed(certification_entry(spec, "research"), EXPECTED_GATE_STATUS["research"]) and certification_snapshot_matches(certification_entry(spec, "research"), phase_artifact_snapshot(spec, "research", ROOT_DIR, DISPLAY_ROOTS))
    prd_complete = prd_status_complete and certification_passed(certification_entry(spec, "prd"), EXPECTED_GATE_STATUS["prd"]) and certification_snapshot_matches(certification_entry(spec, "prd"), phase_artifact_snapshot(spec, "prd", ROOT_DIR, DISPLAY_ROOTS))
    design_complete = design_status_complete and certification_passed(certification_entry(spec, "design"), EXPECTED_GATE_STATUS["design"]) and certification_snapshot_matches(certification_entry(spec, "design"), phase_artifact_snapshot(spec, "design", ROOT_DIR, DISPLAY_ROOTS))
    planning_snapshot_matches = certification_snapshot_matches(
        planning_cert_entry,
        phase_artifact_snapshot(spec, "planning", ROOT_DIR, DISPLAY_ROOTS),
    )
    delivery_has_started = phase_has_recorded_activity(spec, ROOT_DIR, "delivery")
    planning_complete = (
        planning_status_complete
        and certification_passed(planning_cert_entry, EXPECTED_GATE_STATUS["planning"])
        and (planning_snapshot_matches or delivery_has_started)
        and (bool(planning_readiness.get("ready_for_certification")) or delivery_has_started)
    )
    delivery_complete = (
        delivery_status_complete
        and certification_passed(delivery_cert_entry, EXPECTED_GATE_STATUS["delivery"])
        and certification_snapshot_matches(delivery_cert_entry, phase_artifact_snapshot(spec, "delivery", ROOT_DIR, DISPLAY_ROOTS))
        and bool(delivery_readiness.get("ready_for_certification"))
    )
    release_complete = (
        delivery_complete
        and release_status_complete
        and certification_passed(release_cert_entry, EXPECTED_GATE_STATUS["release"])
        and certification_snapshot_matches(release_cert_entry, phase_artifact_snapshot(spec, "release", ROOT_DIR, DISPLAY_ROOTS))
        and bool(release_readiness.get("ready_for_certification"))
    )

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
    research_blockers.extend(phase_incomplete_blockers(spec, "research", research_complete))
    results["research"] = PhaseResult(
        name="research",
        status="complete" if research_complete else ("blocked" if research_blockers else "ready"),
        blockers=research_blockers,
        evidence=[
            f"competitor landscape status: {research_doc_statuses[0] or 'missing'}",
            f"review insights status: {research_doc_statuses[1] or 'missing'}",
            f"feature opportunities status: {research_doc_statuses[2] or 'missing'}",
            certification_evidence(spec, "research"),
        ],
    )

    prd_blockers = []
    if not research_complete:
        prd_blockers.append("Research phase is not approved yet.")
    prd_blockers.extend(phase_incomplete_blockers(spec, "prd", prd_complete))
    results["prd"] = PhaseResult(
        name="prd",
        status="complete" if research_complete and prd_complete else ("blocked" if prd_blockers else "ready"),
        blockers=prd_blockers,
        evidence=[f"prd approval status: {prd_status or 'missing'}", certification_evidence(spec, "prd")],
    )

    design_blockers = []
    if not prd_complete:
        design_blockers.append("PRD is not approved yet.")
    design_blockers.extend(f"Fill {name} in {spec_path}" for name in spec_fields["design"])
    design_blockers.extend(phase_incomplete_blockers(spec, "design", design_complete))
    results["design"] = PhaseResult(
        name="design",
        status="complete" if prd_complete and design_complete else ("blocked" if design_blockers else "ready"),
        blockers=design_blockers,
        evidence=[
            f"ui ux spec approval status: {ui_status or 'missing'}",
            f"i18n strategy approval status: {i18n_status or 'missing'}",
            certification_evidence(spec, "design"),
        ],
    )

    planning_blockers = []
    if not design_complete:
        planning_blockers.append("Design phase is not approved yet.")
    planning_blockers.extend(f"Fill {name} in {spec_path}" for name in spec_fields["planning"])
    planning_blockers.extend(phase_incomplete_blockers(spec, "planning", planning_complete))
    if (
        not planning_complete
        and should_surface_readiness_blocker("planning", plan_file.is_file(), plan_ready, planning_cert_entry)
        and not planning_readiness.get("ready_for_certification")
    ):
        planning_blockers.append(str(planning_readiness.get("summary", "")).strip())
    planning_retry_blocker = prompt_first_retry_blocker(spec, ROOT_DIR, "planning")
    if planning_retry_blocker:
        planning_blockers.append(planning_retry_blocker)
    results["planning"] = PhaseResult(
        name="planning",
        status="complete" if design_complete and planning_complete else ("blocked" if planning_blockers else "ready"),
        blockers=planning_blockers,
        evidence=[
            f"implementation plan ready for execution: {plan_ready or 'missing'}",
            certification_evidence(spec, "planning"),
            str(planning_readiness.get("summary", "")),
        ],
    )

    delivery_blockers = []
    if not planning_complete:
        delivery_blockers.append("Implementation plan is not marked ready for execution yet.")
    delivery_blockers.extend(phase_incomplete_blockers(spec, "delivery", delivery_complete))
    if (
        not delivery_complete
        and should_surface_readiness_blocker("delivery", plan_file.is_file() or release_file.is_file(), delivery_status, delivery_cert_entry)
        and not delivery_readiness.get("ready_for_certification")
    ):
        delivery_blockers.append(str(delivery_readiness.get("summary", "")).strip())
    delivery_retry_blocker = prompt_first_retry_blocker(spec, ROOT_DIR, "delivery")
    if delivery_retry_blocker:
        delivery_blockers.append(delivery_retry_blocker)
    results["delivery"] = PhaseResult(
        name="delivery",
        status="complete" if planning_complete and delivery_complete else ("blocked" if delivery_blockers else "ready"),
        blockers=delivery_blockers,
        evidence=[
            f"delivery status: {delivery_status or 'missing'}",
            certification_evidence(spec, "delivery"),
            str(delivery_readiness.get("summary", "")),
        ],
    )

    release_blockers = []
    if not delivery_complete:
        release_blockers.append("Delivery phase is not verified yet.")
    release_blockers.extend(phase_incomplete_blockers(spec, "release", release_complete))
    if (
        not release_complete
        and should_surface_readiness_blocker("release", release_file.is_file(), release_status, release_cert_entry)
        and not release_readiness.get("ready_for_certification")
    ):
        release_blockers.append(str(release_readiness.get("summary", "")).strip())
    results["release"] = PhaseResult(
        name="release",
        status="complete" if delivery_complete and release_complete else ("blocked" if release_blockers else "ready"),
        blockers=release_blockers,
        evidence=[
            f"release decision: {release_status or 'missing'}",
            certification_evidence(spec, "release"),
            str(release_readiness.get("summary", "")),
        ],
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
    if phase == "research":
        return ("product-research", "Produce approved research evidence", "")
    if phase == "prd":
        return ("research-backed-prd", "Produce a cited PRD from approved research", "")
    if phase == "design":
        return ("ui-ux-governance", "Produce approved UI/UX and i18n design artifacts", "")
    if phase == "planning":
        return ("implementation-planning", "Produce a fine-grained implementation plan from approved artifacts", "")
    if phase == "delivery":
        return ("validated-delivery", "Deliver one validated batch from the approved plan", "")
    return ("supernb-orchestrator", "Run final verification and release readiness checks", "release-readiness + verification-before-completion + ui audit")


def build_command_args(spec: dict[str, Any], phase: str) -> tuple[str, list[str]]:
    command_name, default_goal, capability_hint = command_for_phase(phase)
    constraints = nested_get(spec, "delivery", "constraints")
    quality_bar = nested_get(spec, "delivery", "quality_bar")
    scale_target = nested_get(spec, "delivery", "scale_target_dau") or "10000000"
    if quality_bar:
        constraints = f"{constraints}; quality bar: {quality_bar}" if constraints else f"quality bar: {quality_bar}"
    constraints = f"{constraints}; scale target: {scale_target} dau" if constraints else f"scale target: {scale_target} dau"

    args = [
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
    ]

    artifact_root = artifact_path(spec, "run_status_md").parent
    project_dir = project_root(spec)
    scale_context = f"scale ambition: ship toward a product that can plausibly support at least {scale_target} daily active users, not a demo or niche toy"
    args.extend(["--context-line", scale_context])
    args.extend(["--output-line", f"keep all decisions, artifacts, and delivery depth aligned to a >= {scale_target} DAU product ambition"])

    if command_name in {"product-research", "research-backed-prd", "product-research-prd", "full-product-delivery"}:
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
    if phase in {"planning", "delivery"}:
        args.extend(["--context-line", f"project workspace: {project_dir}"])
        args.extend(["--context-line", f"initiative artifacts root: {artifact_root}"])
        args.extend(["--context-line", "mandatory workflow: use superpowers aggressively for fine-grained planning, TDD, code review, and bounded execution batches"])
        args.extend(["--context-line", "delivery rule: research, PRD, design, and implementation plan must already exist and be updated before claiming code completion"])
        if phase == "planning":
            args.extend(["--output-line", "save or update the implementation plan before any delivery work"])
            args.extend(["--output-line", "break tasks into the smallest safe batches, ideally 2-5 minute chunks with exact file paths and verification steps"])
        else:
            args.extend(["--output-line", "treat this run as one validated delivery batch, not the whole project"])
            args.extend(["--output-line", "update plan and affected initiative artifacts before finishing the batch"])
            args.extend(["--output-line", "run tests first, perform code review, and create a git commit for this batch before reporting completion"])

    return command_name, args


def render_next_command(spec: dict[str, Any], phase: str, output_path: Path) -> dict[str, str]:
    command_name, args = build_command_args(spec, phase)
    subprocess.run([str(ROOT_DIR / "scripts" / "render-command.sh"), *args, "--output-file", str(output_path)], check=True)
    return {"command": command_name, "path": display_path(output_path)}


def save_archived_brief(spec: dict[str, Any], phase: str, brief_dir: Path) -> str:
    command_name, args = build_command_args(spec, phase)
    proc = subprocess.run(
        [
            str(ROOT_DIR / "scripts" / "save-command-brief.sh"),
            *args,
            "--title",
            f"{nested_get(spec, 'initiative', 'title') or nested_get(spec, 'initiative', 'id')} {phase} brief",
            "--brief-dir",
            str(brief_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    marker = "Saved command brief: "
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            return display_path(Path(line[len(marker) :].strip()))
    raise RuntimeError(f"Could not determine archived brief path from save-command-brief output: {proc.stdout}")


def phase_objectives(phase: str) -> list[str]:
    mapping = {
        "research": [
            "Fill the competitor landscape, review insights, and feature opportunities artifacts.",
            "Keep evidence tied to markets, date window, reviewed apps, and global or regional review coverage.",
            "Research should be rich enough to support product decisions, including competitor feature surfaces, monetization patterns, real user likes and dislikes, and market headroom for a 10M-DAU-class product.",
            "Set each research artifact status to approved when it is ready to gate PRD work.",
        ],
        "prd": [
            "Convert approved research into an evidence-backed PRD.",
            "Separate proven conclusions from open hypotheses.",
            "Define a complete product system, not a demo feature list: core capabilities, growth, retention, monetization, launch sequencing, and trust, quality, and scale requirements.",
            "Set PRD approval status to approved when it is ready to gate design work.",
        ],
        "design": [
            "Produce approved UI/UX direction and i18n strategy artifacts.",
            "Use impeccable as a multi-pass design engine: define direction, critique key surfaces, and record final polish and audit notes.",
            "Design should cover flows, states, responsive behavior, trust cues, growth surfaces, conversion and retention surfaces, and localization impacts, not just static screens.",
            "The design artifact should define a real design system, deep-dive key journeys, and preserve enough detail to guide premium implementation quality.",
            "Set both design approval fields to approved before planning starts.",
        ],
        "planning": [
            "Break delivery into validated batches with tests first.",
            "The implementation plan should define technical strategy, dependency and risk controls, review cadence, rollout or recovery expectations, and scale or reliability workstreams.",
            "Populate loop candidates only for bounded tasks with explicit completion promises.",
            "Set Ready for execution to yes when the plan is safe to execute.",
        ],
        "delivery": [
            "Execute the approved plan in small verified batches.",
            "Commit each validated batch and keep localization externalized.",
            "Record the post-implementation impeccable audit in release-readiness before treating delivery as complete.",
            "Each batch should move the product materially toward approved journeys, growth loops, and release readiness, not just produce thin proof-of-concept code.",
            "Set Delivery status to verified when implementation evidence is complete.",
        ],
        "release": [
            "Complete release verification and final UX audit.",
            "Document residual risks, rollout or rollback expectations, capacity assumptions, and release notes.",
            "Set Release decision to ready only when ship criteria are satisfied.",
        ],
    }
    return mapping[phase]


def record_result_command(initiative_id: str, phase: str) -> str:
    cli = supernb_cli_prefix(ROOT_DIR)
    if phase in {"planning", "delivery"}:
        return f"{cli} apply-execution --initiative-id {initiative_id} --packet <execution-packet-dir>"
    return (
        f'{cli} record-result --initiative-id {initiative_id} --phase {phase} '
        '--status "<status>" --summary "<what happened>" '
        '--source manual-override --override-reason "<why packet automation was bypassed>"'
    )


def advance_phase_command(initiative_id: str, phase: str) -> str:
    cli = supernb_cli_prefix(ROOT_DIR)
    defaults = {
        "research": "approved",
        "prd": "approved",
        "design": "approved",
        "planning": "ready",
        "delivery": "verified",
        "release": "ready",
    }
    return f'{cli} advance-phase --initiative-id {initiative_id} --phase {phase} --status {defaults[phase]} --actor "<who approved it>"'


def certify_phase_command(initiative_id: str, phase: str) -> str:
    return f'{supernb_cli_prefix(ROOT_DIR)} certify-phase --initiative-id {initiative_id} --phase {phase}'


def execute_next_command(initiative_id: str) -> str:
    return f'{supernb_cli_prefix(ROOT_DIR)} execute-next --initiative-id {initiative_id}'


def apply_execution_command(initiative_id: str) -> str:
    return f'{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id {initiative_id} --packet <execution-packet-dir>'


def phase_artifact_lines(spec: dict[str, Any], phase: str) -> list[str]:
    artifact_roots = {
        "research": artifact_path(spec, "research_dir"),
        "prd": artifact_path(spec, "prd_dir"),
        "design": artifact_path(spec, "design_dir"),
        "planning": artifact_path(spec, "plan_dir"),
        "delivery": artifact_path(spec, "plan_dir"),
        "release": artifact_path(spec, "release_dir"),
    }
    lines = [f"- Primary artifact root: `{display_path(artifact_roots[phase])}`"]
    lines.append(f"- Initiative index: `{display_path(artifact_path(spec, 'initiative_index'))}`")
    lines.append(f"- Initiative spec: `{display_path(artifact_path(spec, 'run_status_md').parent / 'initiative.yaml')}`")
    return lines


def write_phase_packet(
    spec: dict[str, Any],
    selected_phase: str,
    phase_result: PhaseResult,
    next_command: dict[str, str] | None,
    archived_brief: str | None,
    output_path: Path,
) -> None:
    initiative_id = nested_get(spec, "initiative", "id")
    title = nested_get(spec, "initiative", "title") or initiative_id
    lines = [
        f"# Phase Packet: {selected_phase}",
        "",
        f"- Initiative: `{title}`",
        f"- Generated: `{utc_now()}`",
        f"- Phase status: `{phase_result.status}`",
        "",
        "## Objective",
        "",
    ]
    for item in phase_objectives(selected_phase):
        lines.append(f"- {item}")

    lines.extend(["", "## Artifacts", ""])
    lines.extend(phase_artifact_lines(spec, selected_phase))

    lines.extend(["", "## Gate State", ""])
    if phase_result.blockers:
        for blocker in phase_result.blockers:
            lines.append(f"- Blocker: {blocker}")
    else:
        certification_note = certification_notice(spec, selected_phase)
        if certification_note:
            lines.append(f"- Certification note: {certification_note}")
        else:
            lines.append("- No blocking gate found for this phase.")

    lines.extend(["", "## Evidence Snapshot", ""])
    for evidence in phase_result.evidence:
        lines.append(f"- {evidence}")

    lines.extend(["", "## Execution Assets", ""])
    if next_command:
        lines.append(f"- Next command: `{next_command['path']}`")
        lines.append(f"- Direct execution bridge: `{execute_next_command(initiative_id)}`")
    if archived_brief:
        lines.append(f"- Archived brief: `{archived_brief}`")
    if not next_command and not archived_brief:
        lines.append("- No execution asset generated because the current phase is blocked.")

    lines.extend(["", "## After Execution", ""])
    lines.append(f"- Execute the next command in a harness: `{execute_next_command(initiative_id)}`")
    lines.append(f"- Apply the latest execution packet: `{apply_execution_command(initiative_id)}`")
    lines.append(f"- Certify the artifact set: `{certify_phase_command(initiative_id, selected_phase)}`")
    lines.append(f"- Record the outcome: `{record_result_command(initiative_id, selected_phase)}`")
    lines.append(f"- Advance the gate when ready: `{advance_phase_command(initiative_id, selected_phase)}`")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_run_log(
    spec: dict[str, Any],
    selected_phase: str,
    phase_result: PhaseResult,
    archived_brief: str | None,
    phase_packet_path: Path,
    log_path: Path,
) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")

    lines = [
        f"## {utc_now()}",
        "",
        f"- Phase: `{selected_phase}`",
        f"- Status: `{phase_result.status}`",
        f"- Blocker count: `{len(phase_result.blockers)}`",
        f"- Phase packet: `{display_path(phase_packet_path)}`",
    ]
    if archived_brief:
        lines.append(f"- Archived brief: `{archived_brief}`")
    else:
        lines.append("- Archived brief: not generated")
    lines.append("")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def update_initiative_index(spec: dict[str, Any], results: dict[str, PhaseResult]) -> None:
    index_path = artifact_path(spec, "initiative_index")
    if not index_path.is_file():
        return

    labels = {
        "research": "Research",
        "prd": "PRD",
        "design": "Design",
        "planning": "Planning",
        "delivery": "Delivery",
        "release": "Release",
    }
    text = index_path.read_text(encoding="utf-8")
    for phase in PHASES:
        label = labels[phase]
        replacement = f"- [{'x' if results[phase].status == 'complete' else ' '}] {label}"
        text = re.sub(rf"^- \[[ x]\] {re.escape(label)}$", replacement, text, flags=re.MULTILINE)
    index_path.write_text(text, encoding="utf-8")


def build_markdown(
    spec: dict[str, Any],
    spec_path: Path,
    selected_phase: str,
    results: dict[str, PhaseResult],
    meta: dict[str, str],
    next_command: dict[str, str] | None,
    archived_brief: str | None,
    phase_packet_path: Path,
    run_log_path: Path,
) -> str:
    title = nested_get(spec, "initiative", "title")
    initiative_id = nested_get(spec, "initiative", "id")
    lines = [
        f"# Run Status: {title or initiative_id}",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Generated: `{utc_now()}`",
        f"- Initiative spec: `{display_path(spec_path)}`",
        f"- Selected phase: `{selected_phase}`",
        f"- Phase packet: `{display_path(phase_packet_path)}`",
        f"- Run log: `{display_path(run_log_path)}`",
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
        certification_note = certification_notice(spec, selected_phase)
        if certification_note:
            lines.append(f"- Certification note: {certification_note}")
        else:
            lines.append("- No blocking gate found for the selected phase.")

    lines.extend(["", "## Next Action", ""])
    if next_command is None:
        lines.append("- No command brief was generated because the selected phase is blocked by missing spec fields or unmet gates.")
    else:
        lines.append(f"- Command: `{next_command['command']}`")
        lines.append(f"- Rendered brief: `{next_command['path']}`")
        if archived_brief:
            lines.append(f"- Archived brief: `{archived_brief}`")
        lines.append(f"- Execute via harness: `{execute_next_command(initiative_id)}`")
        lines.append(f"- Apply execution packet: `{apply_execution_command(initiative_id)}`")
        lines.append(f"- Run: `{supernb_cli_prefix(ROOT_DIR)} run --initiative-id {initiative_id}` after phase progress changes")
    lines.append(f"- Certify the current phase: `{certify_phase_command(initiative_id, selected_phase)}`")
    lines.append(f"- Record execution results: `{record_result_command(initiative_id, selected_phase)}`")
    lines.append(f"- Advance phase gate: `{advance_phase_command(initiative_id, selected_phase)}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()

    if not args.initiative_id and not args.spec:
        print("Pass --initiative-id or --spec.", file=sys.stderr)
        return 1

    try:
        spec_path = resolve_spec_path(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not spec_path.is_file():
        print(f"Initiative spec not found: {spec_path}", file=sys.stderr)
        return 1

    spec = load_spec(spec_path)
    global DISPLAY_ROOTS
    DISPLAY_ROOTS = [project_root(spec), ROOT_DIR]
    debug_log(
        spec,
        "start",
        {
            "spec_path": str(spec_path),
            "phase_arg": args.phase,
            "no_next_command": args.no_next_command,
        },
    )
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    results, meta = build_phase_results(spec, spec_path)
    selected_phase = args.phase if args.phase != "auto" else auto_phase(results)
    update_initiative_index(spec, results)

    run_status_md = artifact_path(spec, "run_status_md")
    run_status_json = artifact_path(spec, "run_status_json")
    next_command_md = artifact_path(spec, "next_command_md")
    phase_packet_md = artifact_path(spec, "phase_packet_md")
    run_log_md = artifact_path(spec, "run_log_md")
    command_briefs_dir = artifact_path(spec, "command_briefs_dir")
    run_status_md.parent.mkdir(parents=True, exist_ok=True)
    command_briefs_dir.mkdir(parents=True, exist_ok=True)

    next_command = None
    archived_brief = None
    if not args.no_next_command and results[selected_phase].status != "blocked":
        next_command = render_next_command(spec, selected_phase, next_command_md)
        archived_brief = save_archived_brief(spec, selected_phase, command_briefs_dir)

    write_phase_packet(spec, selected_phase, results[selected_phase], next_command, archived_brief, phase_packet_md)
    append_run_log(spec, selected_phase, results[selected_phase], archived_brief, phase_packet_md, run_log_md)

    markdown = build_markdown(spec, spec_path, selected_phase, results, meta, next_command, archived_brief, phase_packet_md, run_log_md)
    run_status_md.write_text(markdown, encoding="utf-8")

    payload = {
        "initiative_id": initiative_id,
        "selected_phase": selected_phase,
        "generated_at": utc_now(),
        "spec_path": display_path(spec_path),
        "certification_state_path": display_path(certification_state_path(spec)),
        "phase_packet": display_path(phase_packet_md),
        "run_log": display_path(run_log_md),
        "phases": {
            phase: {
                "status": results[phase].status,
                "blockers": results[phase].blockers,
                "evidence": results[phase].evidence,
                "certification": certification_entry(spec, phase),
            }
            for phase in PHASES
        },
        "next_command": next_command,
    }
    run_status_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    debug_log(
        spec,
        "complete",
        {
            "initiative_id": initiative_id,
            "selected_phase": selected_phase,
            "selected_phase_status": results[selected_phase].status,
            "phase_statuses": {phase: results[phase].status for phase in PHASES},
            "phase_blockers": {phase: results[phase].blockers for phase in PHASES if results[phase].blockers},
            "next_command_generated": bool(next_command),
            "run_status_json": display_path(run_status_json),
            "phase_packet_md": display_path(phase_packet_md),
            "archived_brief": archived_brief or "",
        },
    )

    print(f"Initiative: {initiative_id}")
    print(f"Selected phase: {selected_phase} ({results[selected_phase].status})")
    print(f"Run status: {run_status_md}")
    print(f"Run status JSON: {run_status_json}")
    print(f"Phase packet: {phase_packet_md}")
    print(f"Run log: {run_log_md}")
    if next_command:
        print(f"Next command: {next_command_md}")
        if archived_brief:
            print(f"Archived brief: {archived_brief}")
    else:
        print("Next command: not generated because the selected phase is blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
