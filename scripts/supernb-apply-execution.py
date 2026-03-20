#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from lib.supernb_common import (
    append_debug_log as common_append_debug_log,
    load_spec,
    nested_get,
    project_root as common_project_root,
    resolve_existing_path,
    resolve_spec_path as common_resolve_spec_path,
    supernb_cli_prefix,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a saved execution packet into result recording and optional certification.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--packet", required=True, help="Path to an execution packet directory")
    parser.add_argument("--status", default="auto", help="Result status override. Defaults to the packet suggestion.")
    parser.add_argument("--summary", help="Result summary override. Defaults to the packet suggestion.")
    parser.add_argument("--certify", action="store_true", help="Run certify-phase after recording the result")
    parser.add_argument("--apply-certification", action="store_true", help="When certification passes, also apply the phase gate")
    parser.add_argument("--actor", default="supernb", help="Actor name used for certification apply")
    parser.add_argument("--date", help="Approval date forwarded to certify-phase --apply")
    parser.add_argument("--no-rerun", action="store_true", help="Do not rerun supernb after recording or certifying")
    return parser.parse_args()


def project_root(spec: dict[str, Any]) -> Path:
    return common_project_root(spec, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def debug_log(spec: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    common_append_debug_log(spec, ROOT_DIR, "supernb-apply-execution", event, payload)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unique_items(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def workflow_issues_from_suggestion(suggestion: dict[str, Any]) -> list[str]:
    issues = suggestion.get("workflow_issues")
    if isinstance(issues, list):
        return [str(item).strip() for item in issues if str(item).strip()]
    return []


def resolve_evidence_paths(spec: dict[str, Any], packet_dir: Path, values: list[str]) -> tuple[list[str], list[str]]:
    base_dirs = [project_root(spec), packet_dir]
    resolved: list[str] = []
    missing: list[str] = []
    for raw_path in unique_items(values):
        match = resolve_existing_path(raw_path, base_dirs)
        if match is None:
            missing.append(raw_path)
            continue
        resolved.append(str(match))
    return resolved, missing


def apply_certification_follow_up(spec_path: Path, packet_dir: Path) -> str:
    return (
        f"This packet must be recorded first, then inspect blockers with "
        f"`{supernb_cli_prefix(ROOT_DIR)} apply-execution --spec {spec_path} --packet {packet_dir} --certify`."
    )


def run_child(command: list[str]) -> int:
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc.returncode


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
    debug_log(
        spec,
        "start",
        {
            "spec_path": str(spec_path),
            "packet_arg": args.packet,
            "status_arg": args.status,
            "certify": args.certify,
            "apply_certification": args.apply_certification,
            "no_rerun": args.no_rerun,
        },
    )

    packet_dir = Path(args.packet).expanduser().resolve()
    if not packet_dir.is_dir():
        print(f"Execution packet not found: {packet_dir}", file=sys.stderr)
        return 1

    request_path = packet_dir / "request.json"
    suggestion_path = packet_dir / "result-suggestion.json"
    if not request_path.is_file():
        print(f"Missing request metadata in packet: {request_path}", file=sys.stderr)
        return 1
    if not suggestion_path.is_file():
        print(f"Missing result suggestion in packet: {suggestion_path}", file=sys.stderr)
        return 1

    request = read_json(request_path)
    suggestion = read_json(suggestion_path)

    phase = str(request.get("phase", "")).strip()
    if not phase:
        print(f"Missing phase in {request_path}", file=sys.stderr)
        return 1
    packet_initiative_id = str(request.get("initiative_id", "")).strip()
    if packet_initiative_id and packet_initiative_id != initiative_id:
        debug_log(
            spec,
            "initiative-mismatch",
            {
                "initiative_id": initiative_id,
                "packet_initiative_id": packet_initiative_id,
                "packet_dir": str(packet_dir),
            },
        )
        print(
            f"Execution packet initiative mismatch: packet belongs to '{packet_initiative_id}', "
            f"but target initiative is '{initiative_id}'.",
            file=sys.stderr,
        )
        return 1

    status = args.status if args.status != "auto" else str(suggestion.get("suggested_result_status", "")).strip()
    summary = args.summary or str(suggestion.get("suggested_summary", "")).strip()
    suggested_result_status = str(suggestion.get("suggested_result_status", "")).strip().lower()
    if not status:
        print(f"Missing result status suggestion in {suggestion_path}; pass --status explicitly.", file=sys.stderr)
        return 1
    if not summary:
        print(f"Missing summary suggestion in {suggestion_path}; pass --summary explicitly.", file=sys.stderr)
        return 1

    execution_report = suggestion.get("execution_report") or {}
    evidence_paths = [
        str(path)
        for path in [
            packet_dir / "summary.md",
            packet_dir / "response.md",
            packet_dir / "stdout.log",
            packet_dir / "stderr.log",
            packet_dir / "result-suggestion.md",
            packet_dir / "phase-readiness.md",
        ]
        if path.exists()
    ]
    evidence_paths.extend(unique_items([str(item) for item in execution_report.get("evidence_artifacts", [])]))
    phase_readiness = suggestion.get("phase_readiness") or {}
    workflow_issues = workflow_issues_from_suggestion(suggestion)
    resolved_evidence_paths, missing_evidence_paths = resolve_evidence_paths(spec, packet_dir, evidence_paths)

    if missing_evidence_paths:
        debug_log(
            spec,
            "validation-error",
            {
                "initiative_id": initiative_id,
                "phase": phase,
                "missing_evidence_paths": missing_evidence_paths,
            },
        )
        print(
            "Execution packet references evidence artifacts that do not exist: "
            + ", ".join(missing_evidence_paths),
            file=sys.stderr,
        )
        return 1

    if args.apply_certification and status != "succeeded":
        print(
            "--apply-certification requires a succeeded execution result before any gate can be applied. "
            f"This packet would currently be recorded as '{status}' "
            f"(suggested_result_status={suggested_result_status or 'missing'}). "
            f"{apply_certification_follow_up(spec_path, packet_dir)}",
            file=sys.stderr,
        )
        return 1
    if args.apply_certification and suggested_result_status != "succeeded":
        print(
            f"--apply-certification blocked because the execution packet itself did not conclude as succeeded "
            f"(suggested_result_status={suggested_result_status or 'missing'}). "
            f"{apply_certification_follow_up(spec_path, packet_dir)}",
            file=sys.stderr,
        )
        return 1
    if args.apply_certification and not phase_readiness.get("ready_for_certification", False):
        print(
            "--apply-certification blocked because phase-readiness still reports unresolved gaps. "
            f"Review phase-readiness.md or use --certify to inspect the exact blockers first. {apply_certification_follow_up(spec_path, packet_dir)}",
            file=sys.stderr,
        )
        return 1
    if args.apply_certification and workflow_issues:
        print(
            "--apply-certification blocked because the execution packet still reports workflow-trace or commit-policy gaps. "
            f"Review result-suggestion.md and fix the missing superpowers workflow evidence first. {apply_certification_follow_up(spec_path, packet_dir)}",
            file=sys.stderr,
        )
        return 1

    record_command = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "supernb-record-result.py"),
        "--spec",
        str(spec_path),
        "--phase",
        phase,
        "--status",
        status,
        "--summary",
        summary,
        "--source",
        "execution-packet",
        "--source-packet",
        str(packet_dir),
        "--notes-file",
        str(packet_dir / "summary.md"),
    ]
    for evidence_path in unique_items(resolved_evidence_paths):
        record_command.extend(["--artifact-path", evidence_path])
    if args.no_rerun or args.certify or args.apply_certification:
        record_command.append("--no-rerun")

    record_returncode = run_child(record_command)
    if record_returncode != 0:
        return record_returncode

    if args.certify or args.apply_certification:
        certify_command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "supernb-certify-phase.py"),
            "--spec",
            str(spec_path),
            "--phase",
            phase,
        ]
        if args.apply_certification:
            certify_command.extend(["--apply", "--actor", args.actor])
            if args.date:
                certify_command.extend(["--date", args.date])
        certify_returncode = run_child(certify_command)
        if certify_returncode != 0:
            return certify_returncode

    if not args.no_rerun and not args.apply_certification:
        rerun_returncode = run_child([sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--spec", str(spec_path)])
        if rerun_returncode != 0:
            return rerun_returncode
    debug_log(
        spec,
        "complete",
        {
            "initiative_id": initiative_id,
            "phase": phase,
            "packet_dir": str(packet_dir),
            "recorded_status": status,
            "suggested_result_status": suggested_result_status,
            "certify": args.certify,
            "apply_certification": args.apply_certification,
            "no_rerun": args.no_rerun,
            "workflow_issue_count": len(workflow_issues),
            "phase_ready_for_certification": bool(phase_readiness.get("ready_for_certification")),
        },
    )

    print(f"Applied execution packet: {packet_dir}")
    print(f"Recorded result status: {status}")
    print(f"Summary: {summary}")
    if args.certify or args.apply_certification:
        print(f"Certification run: yes ({'apply' if args.apply_certification else 'check-only'})")
    else:
        print("Certification run: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
