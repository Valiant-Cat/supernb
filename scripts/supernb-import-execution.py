#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.supernb_common import (
    artifact_path as common_artifact_path,
    load_spec,
    nested_get,
    project_root as common_project_root,
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
    parser.add_argument("--phase", required=True, help="Phase name for this imported execution")
    parser.add_argument("--report-json", required=True, help="Structured execution report JSON file matching the supernb REPORT contract")
    parser.add_argument("--response-file", help="Optional plain-text or markdown response body to store ahead of the REPORT JSON block")
    parser.add_argument("--stdout-file", help="Optional stdout log to copy into the packet")
    parser.add_argument("--stderr-file", help="Optional stderr log to copy into the packet")
    parser.add_argument("--artifact-path", action="append", default=[], help="Repeatable evidence artifact path to merge into the imported report")
    parser.add_argument("--harness", default="manual-import", help="Harness label to record in the imported packet")
    parser.add_argument("--execution-status", choices=["succeeded", "failed"], default="succeeded", help="Actual execution outcome to record")
    parser.add_argument("--exit-code", type=int, help="Optional process exit code to record")
    return parser.parse_args()


def project_root(spec: dict[str, Any]) -> Path:
    return common_project_root(spec, ROOT_DIR)


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


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


def read_optional_text(path_value: str | None) -> str:
    if not path_value:
        return ""
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


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

    response_prefix = ""
    stdout_text = ""
    stderr_text = ""
    imported_sources = [str(report_path)]
    try:
        response_prefix = read_optional_text(args.response_file)
        stdout_text = read_optional_text(args.stdout_file)
        stderr_text = read_optional_text(args.stderr_file)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for candidate in [args.response_file, args.stdout_file, args.stderr_file]:
        if candidate:
            imported_sources.append(str(Path(candidate).expanduser().resolve()))

    response_text = build_response_text(module, merged_report, response_prefix)
    normalized_report = module.extract_report_json(response_text)
    if normalized_report is None:
        print("Structured report JSON did not pass the supernb REPORT contract validation.", file=sys.stderr)
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
    git_before = module.git_state(project_dir)
    git_after = git_before
    created_commits: list[str] = []

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
        },
    )
    module.write_json(result_suggestion_json, suggestion)
    module.write_result_suggestion_md(result_suggestion_md, initiative_id, suggestion, packet_dir)
    module.write_json(phase_readiness_json, phase_readiness)
    module.write_phase_readiness_md(phase_readiness_md, phase_readiness)

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
