#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.supernb_common import (
    PHASES,
    append_debug_log as common_append_debug_log,
    artifact_path as common_artifact_path,
    load_spec,
    nested_get,
    prompt_first_retry_blocker,
    prompt_first_reassessment_blocker,
    project_root as common_project_root,
    resolve_existing_path,
    resolve_spec_path as common_resolve_spec_path,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]
_EXECUTE_NEXT_MODULE: Any | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a manually executed phase result as a structured supernb execution packet.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", required=True, choices=PHASES, help="Phase name for this imported execution")
    parser.add_argument("--report-json", required=True, help="Structured execution report JSON file matching the supernb REPORT contract")
    parser.add_argument("--response-file", help="Optional plain-text or markdown response body to store ahead of the REPORT JSON block")
    parser.add_argument("--stdout-file", help="Optional stdout log to copy into the packet")
    parser.add_argument("--stderr-file", help="Optional stderr log to copy into the packet")
    parser.add_argument("--artifact-path", action="append", default=[], help="Repeatable evidence artifact path to merge into the imported report")
    parser.add_argument("--harness", default="manual-import", help="Harness label to record in the imported packet")
    parser.add_argument("--source-packet", help="Optional existing execution packet to merge authoritative git/loop evidence from")
    parser.add_argument("--execution-status", choices=["succeeded", "failed"], default="succeeded", help="Actual execution outcome to record")
    parser.add_argument("--exit-code", type=int, help="Optional process exit code to record")
    return parser.parse_args()


def project_root(spec: dict[str, Any]) -> Path:
    return common_project_root(spec, ROOT_DIR)


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def debug_log(spec: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    common_append_debug_log(spec, ROOT_DIR, "supernb-import-execution", event, payload)


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


def resolve_optional_file_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return path


def read_optional_text(path_value: str | None) -> tuple[Path | None, str]:
    path = resolve_optional_file_path(path_value)
    if path is None:
        return None, ""
    return path, path.read_text(encoding="utf-8")


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = [str(item).strip() for item in value if str(item).strip()]
    else:
        values = [str(value).strip()] if str(value).strip() else []
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def resolve_optional_dir_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    path = Path(path_value).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")
    return path


def normalize_phase_name(value: Any) -> str:
    candidate = str(value).strip().lower().strip("`")
    return candidate if candidate in PHASES else ""


def infer_report_phase(report: dict[str, Any]) -> str:
    explicit = normalize_phase_name(report.get("phase"))
    if explicit:
        return explicit

    summary = str(report.get("summary", "")).strip().lower()
    summary_match = re.search(r"\b(research|prd|design|planning|delivery|release)\s+phase\b", summary)
    if summary_match:
        return summary_match.group(1)

    loop_execution = report.get("loop_execution") or {}
    haystacks = [
        str(loop_execution.get("completion_promise", "")).lower(),
        str(loop_execution.get("state_file", "")).lower(),
        str(loop_execution.get("evidence", "")).lower(),
    ]
    found: set[str] = set()
    for phase in PHASES:
        markers = [f"{phase} batch complete", f"-{phase}-", f"/{phase}-", f"_{phase}_"]
        if any(any(marker in haystack for marker in markers) for haystack in haystacks if haystack):
            found.add(phase)
    if len(found) == 1:
        return next(iter(found))
    return ""


def build_response_text(module: Any, report_payload: dict[str, Any], response_prefix: str) -> str:
    prefix = response_prefix.strip()
    if not prefix:
        prefix = "# Imported Execution\n\n- Imported a manually executed run into a structured supernb packet."
    report_block = json.dumps(report_payload, indent=2)
    return f"{prefix.rstrip()}\n\n{module.REPORT_START}\n{report_block}\n{module.REPORT_END}\n"


def build_summary_md(
    initiative_id: str,
    phase: str,
    harness: str,
    execution_status: str,
    summary: str,
    imported_sources: list[str],
) -> str:
    lines = [
        "# Imported Execution Summary",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Phase: `{phase}`",
        f"- Imported at: `{utc_now()}`",
        f"- Harness: `{harness}`",
        f"- Execution status: `{execution_status}`",
        f"- Summary: {summary}",
        "",
        "## Imported Sources",
        "",
    ]
    if imported_sources:
        for source in imported_sources:
            lines.append(f"- `{source}`")
    else:
        lines.append("- Structured report JSON only")
    return "\n".join(lines) + "\n"


def resolve_evidence_artifacts(
    module: Any,
    raw_paths: list[str],
    project_dir: Path,
    search_roots: list[Path],
) -> tuple[list[str], list[str]]:
    resolved_artifacts: list[str] = []
    missing_artifacts: list[str] = []
    seen: set[str] = set()
    for raw_path in raw_paths:
        candidate = str(raw_path).strip()
        if not candidate:
            continue
        resolved = resolve_existing_path(candidate, search_roots)
        if resolved is None:
            missing_artifacts.append(candidate)
            continue
        rendered = module.display_path(resolved if resolved.is_absolute() else (project_dir / resolved).resolve())
        if rendered in seen:
            continue
        seen.add(rendered)
        resolved_artifacts.append(rendered)
    return resolved_artifacts, missing_artifacts


def load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def load_source_packet_context(packet_dir: Path) -> dict[str, Any]:
    request_path = packet_dir / "request.json"
    if not request_path.is_file():
        raise FileNotFoundError(f"Source packet request.json not found: {request_path}")
    request_payload = load_json_dict(request_path)
    return {
        "packet_dir": packet_dir,
        "request_path": request_path,
        "request": request_payload,
        "harness": str(request_payload.get("harness", "")).strip(),
        "phase": normalize_phase_name(request_payload.get("phase")),
    }


def derive_source_loop_execution(report: dict[str, Any], source_context: dict[str, Any]) -> dict[str, Any] | None:
    request_payload = source_context["request"]
    loop_contract = request_payload.get("ralph_loop")
    if not isinstance(loop_contract, dict) or not loop_contract:
        return None

    existing_loop = report.get("loop_execution") if isinstance(report.get("loop_execution"), dict) else {}
    audit_summary = request_payload.get("ralph_loop_audit_summary")
    if not isinstance(audit_summary, dict):
        audit_summary = {}
    final_status = str(audit_summary.get("final_status", "")).strip()
    existing_final_iteration = int(existing_loop.get("final_iteration", 0) or 0)
    source_last_iteration = int(audit_summary.get("last_iteration", 0) or 0)
    exit_reason = str(existing_loop.get("exit_reason", "")).strip()
    if not exit_reason:
        if final_status == "state_removed":
            exit_reason = "completion promise became true"
        elif final_status:
            exit_reason = final_status.replace("_", "-")

    return {
        "used": True,
        "mode": "ralph-loop",
        "completion_promise": str(loop_contract.get("completion_promise", "")).strip(),
        "state_file": str(loop_contract.get("state_file", "")).strip(),
        "max_iterations": max(int(loop_contract.get("max_iterations", 0) or 0), 0),
        "final_iteration": max(existing_final_iteration, source_last_iteration),
        "exit_reason": exit_reason,
        "evidence": str(loop_contract.get("audit_summary_file", "")).strip(),
    }


def merge_source_packet_fields(report: dict[str, Any], source_context: dict[str, Any]) -> dict[str, Any]:
    merged = dict(report)
    request_payload = source_context["request"]
    original_loop = merged.get("loop_execution") if isinstance(merged.get("loop_execution"), dict) else {}
    original_loop_evidence = str(original_loop.get("evidence", "")).strip()

    source_loop_execution = derive_source_loop_execution(merged, source_context)
    if source_loop_execution:
        merged["loop_execution"] = source_loop_execution
        evidence_artifacts = ensure_list(merged.get("evidence_artifacts"))
        source_loop_evidence = str(source_loop_execution.get("evidence", "")).strip()
        if original_loop_evidence and source_loop_evidence and original_loop_evidence != source_loop_evidence:
            evidence_artifacts = [item for item in evidence_artifacts if item.strip() != original_loop_evidence]
        if source_loop_evidence:
            evidence_artifacts.append(source_loop_evidence)
        merged["evidence_artifacts"] = ensure_list(evidence_artifacts)

    source_commits = ensure_list(request_payload.get("commits_created"))
    if source_commits and not merged.get("batch_commits"):
        merged["batch_commits"] = source_commits
    return merged


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
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1
    if args.harness == "claude-code-prompt":
        reassessment_blocker = prompt_first_reassessment_blocker(spec, ROOT_DIR, spec_path, args.phase)
        if reassessment_blocker:
            debug_log(
                spec,
                "reassessment-blocked",
                {
                    "spec_path": str(spec_path),
                    "phase": args.phase,
                    "harness": args.harness,
                },
            )
            print(reassessment_blocker, file=sys.stderr)
            return 1
        retry_blocker = prompt_first_retry_blocker(spec, ROOT_DIR, args.phase)
        if retry_blocker:
            debug_log(
                spec,
                "retry-blocked",
                {
                    "spec_path": str(spec_path),
                    "phase": args.phase,
                    "harness": args.harness,
                },
            )
            print(retry_blocker, file=sys.stderr)
            return 1
    debug_log(
        spec,
        "start",
        {
            "spec_path": str(spec_path),
            "phase": args.phase,
            "harness": args.harness,
            "report_json": args.report_json,
            "execution_status": args.execution_status,
        },
    )

    module = load_execute_next_module()
    project_dir = project_root(spec)
    module.DISPLAY_ROOTS = [project_dir, ROOT_DIR]

    report_path = Path(args.report_json).expanduser().resolve()
    if not report_path.is_file():
        print(f"Structured report JSON not found: {report_path}", file=sys.stderr)
        return 1

    try:
        raw_report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {report_path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(raw_report, dict):
        print(f"Structured report must be a JSON object: {report_path}", file=sys.stderr)
        return 1

    merged_report = dict(raw_report)
    merged_report["evidence_artifacts"] = ensure_list(merged_report.get("evidence_artifacts")) + ensure_list(args.artifact_path)
    merged_report["evidence_artifacts"] = ensure_list(merged_report["evidence_artifacts"])

    imported_sources = [str(report_path)]
    source_packet_dir: Path | None = None
    source_context: dict[str, Any] | None = None
    try:
        response_file_path, response_prefix = read_optional_text(args.response_file)
        stdout_file_path, stdout_text = read_optional_text(args.stdout_file)
        stderr_file_path, stderr_text = read_optional_text(args.stderr_file)
        source_packet_dir = resolve_optional_dir_path(args.source_packet)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for candidate in [response_file_path, stdout_file_path, stderr_file_path]:
        if candidate is not None:
            imported_sources.append(str(candidate))

    evidence_search_roots = [project_dir, report_path.parent]
    for candidate in [response_file_path, stdout_file_path, stderr_file_path]:
        if candidate is not None:
            evidence_search_roots.append(candidate.parent)
    if source_packet_dir is not None:
        try:
            source_context = load_source_packet_context(source_packet_dir)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        source_phase = source_context.get("phase", "")
        if source_phase and source_phase != args.phase:
            print(
                f"Source packet phase mismatch: packet is bound to `{source_phase}` but import requested `{args.phase}`.",
                file=sys.stderr,
            )
            return 1
        merged_report = merge_source_packet_fields(merged_report, source_context)
        imported_sources.append(str(source_packet_dir))
        evidence_search_roots.append(source_packet_dir)

    resolved_evidence_artifacts, missing_evidence_artifacts = resolve_evidence_artifacts(
        module,
        ensure_list(merged_report.get("evidence_artifacts")),
        project_dir,
        evidence_search_roots,
    )
    if missing_evidence_artifacts:
        debug_log(
            spec,
            "validation-error",
            {
                "phase": args.phase,
                "missing_evidence_artifacts": missing_evidence_artifacts,
            },
        )
        print(
            "Structured report references evidence artifacts that do not exist: "
            + ", ".join(missing_evidence_artifacts),
            file=sys.stderr,
        )
        return 1
    merged_report["evidence_artifacts"] = resolved_evidence_artifacts

    response_text = build_response_text(module, merged_report, response_prefix)
    normalized_report = module.extract_report_json(response_text)
    if normalized_report is None:
        debug_log(
            spec,
            "contract-error",
            {
                "phase": args.phase,
                "report_json": str(report_path),
            },
        )
        print("Structured report JSON did not pass the supernb REPORT contract validation.", file=sys.stderr)
        return 1
    if args.harness == "claude-code-prompt":
        report_phase = infer_report_phase(normalized_report)
        if not report_phase:
            debug_log(
                spec,
                "validation-error",
                {
                    "phase": args.phase,
                    "harness": args.harness,
                    "reason": "missing-report-phase",
                },
            )
            print(
                "Prompt-first structured report is missing a bound phase marker. "
                f"Refresh the managed prompt files for `{args.phase}` and regenerate the report before importing.",
                file=sys.stderr,
            )
            return 1
        if report_phase != args.phase:
            debug_log(
                spec,
                "validation-error",
                {
                    "phase": args.phase,
                    "harness": args.harness,
                    "report_phase": report_phase,
                    "reason": "phase-mismatch",
                },
            )
            print(
                f"Prompt-first structured report phase mismatch: report is bound to `{report_phase}` but import requested `{args.phase}`. "
                "Refresh the managed prompt files for the active phase before importing.",
                file=sys.stderr,
            )
            return 1

    executions_dir = artifact_path(spec, "executions_dir")
    packet_dir = executions_dir / f"{timestamp_slug()}-{args.phase}-{args.harness}"
    packet_dir.mkdir(parents=True, exist_ok=True)

    prompt_copy_path = packet_dir / "prompt.md"
    prompt_with_report_path = packet_dir / "prompt-with-report.md"
    response_path = packet_dir / "response.md"
    stdout_path = packet_dir / "stdout.log"
    stderr_path = packet_dir / "stderr.log"
    summary_path = packet_dir / "summary.md"
    request_path = packet_dir / "request.json"
    result_suggestion_json = packet_dir / "result-suggestion.json"
    result_suggestion_md = packet_dir / "result-suggestion.md"
    phase_readiness_json = packet_dir / "phase-readiness.json"
    phase_readiness_md = packet_dir / "phase-readiness.md"

    prompt_copy_path.write_text("# Imported Execution Packet\n\n- No prompt was generated because this packet was imported manually.\n", encoding="utf-8")
    prompt_with_report_path.write_text("# Imported Execution Packet\n\n- No prompt-with-report was generated because this packet was imported manually.\n", encoding="utf-8")
    response_path.write_text(response_text, encoding="utf-8")
    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")
    summary_text = normalized_report.get("summary") or "Imported execution packet."
    summary_path.write_text(
        build_summary_md(initiative_id, args.phase, args.harness, args.execution_status, summary_text, imported_sources),
        encoding="utf-8",
    )

    phase_readiness = module.build_phase_readiness(spec, args.phase)
    if source_context is not None:
        source_request = source_context["request"]
        git_before = source_request.get("git_before") if isinstance(source_request.get("git_before"), dict) else module.git_state(project_dir)
        git_after = source_request.get("git_after") if isinstance(source_request.get("git_after"), dict) else git_before
        created_commits = ensure_list(source_request.get("commits_created"))
        if not created_commits:
            created_commits = module.validated_report_batch_commits(project_dir, normalized_report, git_after)
    else:
        git_before = module.git_state(project_dir)
        git_after = git_before
        created_commits = module.validated_report_batch_commits(project_dir, normalized_report, git_after)

    suggestion = module.build_result_suggestion(
        args.phase,
        args.harness,
        args.execution_status,
        False,
        args.exit_code,
        response_text,
        stderr_text,
        packet_dir,
        project_dir,
        phase_readiness,
        git_before,
        git_after,
        created_commits,
    )

    module.write_json(
        request_path,
        {
            "initiative_id": initiative_id,
            "phase": args.phase,
            "harness": args.harness,
            "generated_at": utc_now(),
            "prompt_source": "manual-import",
            "prompt_copy": module.display_path(prompt_copy_path),
            "prompt_with_report": module.display_path(prompt_with_report_path),
            "project_dir": str(project_dir),
            "dry_run": False,
            "command": ["manual-import"],
            "cli_args": [],
            "git_before": git_before,
            "git_after": git_after,
            "commits_created": created_commits,
            "source_packet": str(source_packet_dir) if source_packet_dir is not None else "",
        },
    )
    module.write_json(result_suggestion_json, suggestion)
    module.write_result_suggestion_md(result_suggestion_md, initiative_id, suggestion, packet_dir)
    module.write_json(phase_readiness_json, phase_readiness)
    module.write_phase_readiness_md(phase_readiness_md, phase_readiness)
    debug_log(
        spec,
        "complete",
        {
            "initiative_id": initiative_id,
            "phase": args.phase,
            "harness": args.harness,
            "packet_dir": module.display_path(packet_dir),
            "result_suggestion": module.display_path(result_suggestion_md),
            "phase_readiness": module.display_path(phase_readiness_md),
            "evidence_artifact_count": len(resolved_evidence_artifacts),
            "suggested_result_status": suggestion.get("suggested_result_status", ""),
            "workflow_issue_count": len(suggestion.get("workflow_issues", [])),
        },
    )

    print(f"Initiative: {initiative_id}")
    print(f"Phase: {args.phase}")
    print(f"Harness: {args.harness}")
    print(f"Project dir: {project_dir}")
    print(f"Execution packet: {packet_dir}")
    print(f"Summary: {summary_path}")
    print(f"Response: {response_path}")
    print(f"Result suggestion: {result_suggestion_md}")
    print(f"Phase readiness: {phase_readiness_md}")
    print("Status: imported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
