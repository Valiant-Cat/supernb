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
    artifact_path as common_artifact_path,
    certification_snapshot_matches,
    certification_state_path as common_certification_state_path,
    display_path as common_display_path,
    load_certification_state,
    load_spec,
    nested_get,
    phase_artifact_snapshot,
    phase_targets as common_phase_targets,
    project_root as common_project_root,
    resolve_spec_path as common_resolve_spec_path,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]

METADATA_FIELDS = {
    "Initiative ID",
    "Product",
    "Research date",
    "Prepared",
    "Status",
    "Approval status",
    "Ready for execution",
    "Delivery status",
    "Release decision",
    "Approved by",
    "Approved on",
}

_EXECUTE_NEXT_MODULE: Any | None = None


@dataclass
class Issue:
    path: Path
    line_no: int
    message: str
    line_text: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Certify whether a phase artifact set looks complete enough to advance.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", choices=PHASES, help="Phase to inspect. Defaults to the current selected phase.")
    parser.add_argument("--apply", action="store_true", help="Apply the recommended gate status when the phase passes certification")
    parser.add_argument("--actor", default="supernb", help="Actor name used when --apply is set")
    parser.add_argument("--date", default=today_stamp(), help="Approval date used when --apply is set")
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


def current_phase_from_run_status(spec: dict[str, Any]) -> str:
    run_status_json = artifact_path(spec, "run_status_json")
    if not run_status_json.is_file():
        raise FileNotFoundError(f"Run status JSON not found: {run_status_json}. Run ./scripts/supernb run first or pass --phase.")
    import json

    payload = json.loads(run_status_json.read_text(encoding="utf-8"))
    phase = str(payload.get("selected_phase", "")).strip()
    if not phase:
        raise ValueError(f"selected_phase missing in {run_status_json}")
    return phase


def phase_targets(spec: dict[str, Any], phase: str) -> list[Path]:
    return common_phase_targets(spec, phase, ROOT_DIR)


def packet_metadata(packet: Path) -> dict[str, Any]:
    request_path = packet / "request.json"
    suggestion_path = packet / "result-suggestion.json"
    metadata: dict[str, Any] = {
        "packet": packet,
        "request_path": request_path,
        "suggestion_path": suggestion_path,
        "initiative_id": "",
        "phase": "",
        "dry_run": False,
        "execution_status": "",
        "suggested_result_status": "",
        "valid": False,
    }
    if not request_path.is_file() or not suggestion_path.is_file():
        return metadata
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        suggestion = json.loads(suggestion_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return metadata
    metadata.update(
        {
            "initiative_id": str(request.get("initiative_id", "")).strip(),
            "phase": str(request.get("phase", "")).strip(),
            "dry_run": bool(request.get("dry_run")),
            "execution_status": str(suggestion.get("execution_status", "")).strip().lower(),
            "suggested_result_status": str(suggestion.get("suggested_result_status", "")).strip().lower(),
            "valid": True,
        }
    )
    return metadata


def latest_execution_packet(spec: dict[str, Any], phase: str) -> Path | None:
    executions_dir = artifact_path(spec, "executions_dir")
    if not executions_dir.is_dir():
        return None
    initiative_id = nested_get(spec, "initiative", "id")
    candidates = [path for path in executions_dir.iterdir() if path.is_dir() and f"-{phase}-" in path.name]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)

    matching_packets: list[dict[str, Any]] = []
    fallback_packets: list[dict[str, Any]] = []
    for packet in candidates:
        metadata = packet_metadata(packet)
        if metadata["initiative_id"] and metadata["initiative_id"] != initiative_id:
            continue
        if metadata["phase"] and metadata["phase"] != phase:
            continue
        fallback_packets.append(metadata)
        if metadata["valid"] and not metadata["dry_run"] and metadata["execution_status"] not in {"prepared", "unsupported"}:
            matching_packets.append(metadata)

    if matching_packets:
        return matching_packets[0]["packet"]
    if fallback_packets:
        return fallback_packets[0]["packet"]
    return None


def execution_compliance_findings(spec: dict[str, Any], phase: str) -> list[str]:
    if phase not in {"planning", "delivery"}:
        return []
    packet = latest_execution_packet(spec, phase)
    if packet is None:
        return [f"No execution packet found for {phase}; run ./scripts/supernb execute-next first."]
    suggestion_path = packet / "result-suggestion.json"
    request_path = packet / "request.json"
    if not request_path.is_file():
        return [f"Execution packet is missing request.json: {display_path(request_path)}"]
    if not suggestion_path.is_file():
        return [f"Execution packet is missing result-suggestion.json: {display_path(suggestion_path)}"]
    import json

    request = json.loads(request_path.read_text(encoding="utf-8"))
    suggestion = json.loads(suggestion_path.read_text(encoding="utf-8"))
    initiative_id = nested_get(spec, "initiative", "id")
    packet_initiative = str(request.get("initiative_id", "")).strip()
    packet_phase = str(request.get("phase", "")).strip()
    if bool(request.get("dry_run")):
        return [f"Latest {phase} execution packet is a dry run only; run ./scripts/supernb execute-next without --dry-run or import a manual execution packet first."]
    findings: list[str] = []
    if packet_initiative and packet_initiative != initiative_id:
        findings.append(f"Latest execution packet belongs to initiative {packet_initiative}, not {initiative_id}.")
    if packet_phase and packet_phase != phase:
        findings.append(f"Latest execution packet phase is {packet_phase}, not {phase}.")
    execution_status = str(suggestion.get("execution_status", "")).strip().lower()
    if execution_status == "unsupported":
        findings.append(
            f"Latest {phase} execution packet only prepared a manual handoff (execution_status=unsupported); import a real execution result before certification."
        )

    suggested_result = str(suggestion.get("suggested_result_status", "")).strip().lower()
    if phase == "delivery" and suggested_result != "succeeded":
        findings.append(f"Latest delivery execution packet is not completion-grade: suggested_result_status={suggested_result or 'missing'}.")

    issues = suggestion.get("workflow_issues")
    if isinstance(issues, list) and issues:
        findings.extend(str(item).strip() for item in issues if str(item).strip())

    if phase == "delivery":
        module = load_execute_next_module()
        release_file = artifact_path(spec, "release_dir") / "release-readiness.md"
        expected_sections = [
            "Verification Summary",
            "Localization Summary",
            "Operational Readiness",
            "Rollout And Rollback Plan",
            "Scale Launch Controls",
            "Post-Launch Watchlist",
        ]
        release_check = module.inspect_artifact_readiness(release_file, "delivery", expected_sections)
        if not release_check.get("exists", False):
            findings.append(f"Delivery should update release-readiness inputs, but the artifact is missing: {release_check['path']}")
        else:
            if release_check.get("missing_sections"):
                findings.append(
                    f"Delivery release-readiness is missing sections: {', '.join(release_check['missing_sections'])}"
                )
            if release_check.get("thin_sections"):
                findings.append(
                    f"Delivery release-readiness has thin sections: {', '.join(release_check['thin_sections'])}"
                )
            for semantic_issue in release_check.get("semantic_issues", []):
                findings.append(f"Delivery release-readiness semantic gap: {semantic_issue}")
    return findings


def recommended_gate_status(phase: str) -> str:
    mapping = {
        "research": "approved",
        "prd": "approved",
        "design": "approved",
        "planning": "ready",
        "delivery": "verified",
        "release": "ready",
    }
    return mapping[phase]


def line_is_placeholder_bullet(stripped: str) -> bool:
    match = re.match(r"^- ([^:]+):\s*$", stripped)
    if not match:
        return False
    label = match.group(1).strip()
    return label not in METADATA_FIELDS


def line_is_placeholder_numbered(stripped: str) -> bool:
    return bool(re.match(r"^\d+\.\s+[^:]+:\s*$", stripped))


def line_is_empty_table_row(stripped: str) -> bool:
    if not stripped.startswith("|"):
        return False
    if re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", stripped):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return all(cell == "" for cell in cells)


def line_has_template_marker(stripped: str) -> bool:
    patterns = [
        r"\bPattern \d+:\s*$",
        r"\bGap \d+:\s*$",
        r"\bJourney \d+:\s*$",
        r"\bGoal \d+:\s*$",
        r"\bNon-goal \d+:\s*$",
        r"\bPage \d+\s*$",
        r"\bHotspot \d+:\s*$",
    ]
    return any(re.search(pattern, stripped) for pattern in patterns)


def line_is_unchecked_release_checkbox(stripped: str, phase: str) -> bool:
    return phase == "release" and stripped.startswith("- [ ] ")


def collect_issues(path: Path, phase: str) -> list[Issue]:
    issues: list[Issue] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if "{{" in stripped and "}}" in stripped:
            issues.append(Issue(path, idx, "Unresolved template variable remains", stripped))
            continue
        if line_is_placeholder_bullet(stripped):
            issues.append(Issue(path, idx, "Blank placeholder field remains", stripped))
            continue
        if line_is_placeholder_numbered(stripped):
            issues.append(Issue(path, idx, "Blank numbered placeholder remains", stripped))
            continue
        if line_is_empty_table_row(stripped):
            issues.append(Issue(path, idx, "Empty table row remains", stripped))
            continue
        if line_has_template_marker(stripped) and stripped.endswith(":"):
            issues.append(Issue(path, idx, "Template marker still present", stripped))
            continue
        if line_is_unchecked_release_checkbox(stripped, phase):
            issues.append(Issue(path, idx, "Unchecked release checklist item remains", stripped))
    return issues


def append_run_log(
    log_path: Path,
    phase: str,
    recommendation: str,
    passed: bool,
    applied: bool,
    report_path: Path,
) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")
    lines = [
        f"## {utc_now()} certification",
        "",
        f"- Phase: `{phase}`",
        f"- Passed: `{'yes' if passed else 'no'}`",
        f"- Recommended gate status: `{recommendation}`",
        f"- Applied automatically: `{'yes' if applied else 'no'}`",
        f"- Certification report: `{display_path(report_path)}`",
        "",
    ]
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def write_report(
    spec: dict[str, Any],
    phase: str,
    issues: list[Issue],
    execution_findings: list[str],
    readiness: dict[str, Any],
    report_path: Path,
    applied: bool,
) -> None:
    recommendation = recommended_gate_status(phase)
    readiness_ok = bool(readiness.get("ready_for_certification"))
    lines = [
        "# Phase Certification",
        "",
        f"- Initiative ID: `{nested_get(spec, 'initiative', 'id')}`",
        f"- Phase: `{phase}`",
        f"- Recorded: `{utc_now()}`",
        f"- Passed: `{'yes' if not issues and not execution_findings and readiness_ok else 'no'}`",
        f"- Recommended gate status: `{recommendation}`",
        f"- Applied automatically: `{'yes' if applied else 'no'}`",
        "",
        "## Checked Artifacts",
        "",
    ]
    checked_targets = phase_targets(spec, phase)
    if phase == "delivery":
        checked_targets = [*checked_targets, artifact_path(spec, "release_dir") / "release-readiness.md"]
    for target in checked_targets:
        lines.append(f"- `{display_path(target)}`")

    lines.extend(
        [
            "",
            "## Phase Readiness",
            "",
            f"- Ready for certification: `{'yes' if readiness_ok else 'no'}`",
            f"- Summary: {readiness.get('summary', '')}",
            f"- Missing sections: `{readiness.get('total_missing_sections', 0)}`",
            f"- Thin sections: `{readiness.get('total_thin_sections', 0)}`",
            f"- Placeholder lines: `{readiness.get('total_placeholders', 0)}`",
            f"- Semantic issues: `{readiness.get('total_semantic_issues', 0)}`",
            f"- Traceability issues: `{readiness.get('total_traceability_issues', 0)}`",
        ]
    )

    lines.extend(["", "## Findings", ""])
    if issues:
        for issue in issues:
            lines.append(f"- `{display_path(issue.path)}:{issue.line_no}` {issue.message}: `{issue.line_text}`")
    for finding in execution_findings:
        lines.append(f"- execution compliance: {finding}")
    for check in readiness.get("artifact_checks", []):
        if check.get("missing_sections"):
            lines.append(f"- `{check['path']}` missing sections: {', '.join(check['missing_sections'])}")
        if check.get("thin_sections"):
            lines.append(f"- `{check['path']}` thin sections: {', '.join(check['thin_sections'])}")
        for semantic_issue in check.get("semantic_issues", []):
            lines.append(f"- `{check['path']}` semantic gap: {semantic_issue}")
    for check in readiness.get("traceability_checks", []):
        for traceability_issue in check.get("issues", []):
            lines.append(
                f"- traceability `{check.get('name')}` ({check.get('source_path')} -> {check.get('target_path')}): {traceability_issue}"
            )
    if not issues and not execution_findings and readiness_ok:
        lines.append("- No unresolved template placeholders, missing sections, thin sections, semantic readiness gaps, or cross-phase traceability gaps were detected.")

    lines.extend(["", "## Next Action", ""])
    if issues or execution_findings or not readiness_ok:
        lines.append(f"- Resolve the findings above, then rerun `./scripts/supernb certify-phase --initiative-id {nested_get(spec, 'initiative', 'id')} --phase {phase}`.")
    elif applied:
        lines.append(f"- The gate was advanced automatically to `{recommendation}`.")
    else:
        lines.append(f"- You can now advance the gate with `./scripts/supernb advance-phase --initiative-id {nested_get(spec, 'initiative', 'id')} --phase {phase} --status {recommendation} --actor <who approved it>`.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_certification_state(
    spec: dict[str, Any],
    phase: str,
    passed: bool,
    recommendation: str,
    readiness: dict[str, Any],
    report_path: Path,
) -> None:
    state_path = certification_state_path(spec)
    state = load_certification_state(state_path)
    phases = state.setdefault("phases", {})
    if not isinstance(phases, dict):
        phases = {}
        state["phases"] = phases
    phases[phase] = {
        "checked_at": utc_now(),
        "passed": passed,
        "recommended_gate_status": recommendation,
        "report_path": display_path(report_path),
        "artifact_snapshot": phase_artifact_snapshot(spec, phase, ROOT_DIR, DISPLAY_ROOTS),
        "summary": readiness.get("summary", ""),
        "ready_for_certification": bool(readiness.get("ready_for_certification")),
        "total_missing_sections": int(readiness.get("total_missing_sections", 0)),
        "total_thin_sections": int(readiness.get("total_thin_sections", 0)),
        "total_placeholders": int(readiness.get("total_placeholders", 0)),
        "total_semantic_issues": int(readiness.get("total_semantic_issues", 0)),
        "total_traceability_issues": int(readiness.get("total_traceability_issues", 0)),
    }
    state["initiative_id"] = nested_get(spec, "initiative", "id")
    state["updated_at"] = utc_now()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


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
    global DISPLAY_ROOTS
    DISPLAY_ROOTS = [project_root(spec), ROOT_DIR]
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    phase = args.phase or current_phase_from_run_status(spec)
    issues: list[Issue] = []
    for target in phase_targets(spec, phase):
        if not target.is_file():
            print(f"Artifact not found for phase {phase}: {target}", file=sys.stderr)
            return 1
        issues.extend(collect_issues(target, phase))
    readiness = build_phase_readiness(spec, phase)
    execution_findings = execution_compliance_findings(spec, phase)
    passed = not issues and not execution_findings and bool(readiness.get("ready_for_certification"))

    results_dir = artifact_path(spec, "phase_results_dir")
    run_log_path = artifact_path(spec, "run_log_md")
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / f"{timestamp_slug()}-{phase}-certification.md"

    applied = False
    if args.apply and passed:
        write_certification_state(spec, phase, passed, recommended_gate_status(phase), readiness, report_path)
        subprocess.run(
            [
                sys.executable,
                str(ROOT_DIR / "scripts" / "supernb-advance-phase.py"),
                "--spec",
                str(spec_path),
                "--phase",
                phase,
                "--status",
                recommended_gate_status(phase),
                "--actor",
                args.actor,
                "--date",
                args.date,
            ],
            check=True,
        )
        applied = True

    write_report(spec, phase, issues, execution_findings, readiness, report_path, applied)
    write_certification_state(spec, phase, passed, recommended_gate_status(phase), readiness, report_path)
    append_run_log(run_log_path, phase, recommended_gate_status(phase), passed, applied, report_path)

    print(f"Phase certification report: {report_path}")
    print(f"Passed: {'yes' if passed else 'no'}")
    print(f"Recommended gate status: {recommended_gate_status(phase)}")
    if not passed:
        print(f"Line issue count: {len(issues)}")
        print(f"Execution compliance findings: {len(execution_findings)}")
        print(
            "Readiness gaps: "
            f"missing={readiness.get('total_missing_sections', 0)} "
            f"thin={readiness.get('total_thin_sections', 0)} "
            f"placeholders={readiness.get('total_placeholders', 0)} "
            f"semantic={readiness.get('total_semantic_issues', 0)}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
