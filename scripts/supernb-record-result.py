#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.supernb_common import (
    append_debug_log as common_append_debug_log,
    artifact_path as common_artifact_path,
    display_path as common_display_path,
    load_spec,
    nested_get,
    project_root as common_project_root,
    resolve_existing_path,
    resolve_spec_path as common_resolve_spec_path,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]
RESULT_STATUSES = ["succeeded", "blocked", "needs-follow-up", "manual-follow-up", "not-run", "failed"]
RESULT_SOURCES = ["manual-override", "execution-packet"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a supernb phase execution result and optionally re-evaluate the initiative.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", help="Phase name. Defaults to the current selected phase from run-status.json.")
    parser.add_argument("--status", required=True, choices=RESULT_STATUSES, help="Outcome label for the recorded phase result")
    parser.add_argument("--summary", required=True, help="One-line execution summary")
    parser.add_argument("--source", choices=RESULT_SOURCES, default="manual-override", help="Whether this result is a manual override or sourced from an execution packet")
    parser.add_argument("--override-reason", help="Why a manual override is necessary. Required for manual overrides.")
    parser.add_argument("--source-packet", help="Execution packet directory when --source execution-packet is used")
    parser.add_argument("--notes-file", help="Optional markdown/text file to embed into the result record")
    parser.add_argument("--artifact-path", action="append", default=[], help="Repeatable evidence artifact path")
    parser.add_argument("--no-rerun", action="store_true", help="Do not invoke supernb run after recording the result")
    return parser.parse_args()


def display_path(path: Path) -> str:
    return common_display_path(path, DISPLAY_ROOTS)


def project_root(spec: dict[str, Any]) -> Path:
    return common_project_root(spec, ROOT_DIR)


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def debug_log(spec: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    common_append_debug_log(spec, ROOT_DIR, "supernb-record-result", event, payload)


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


def append_to_run_log(
    log_path: Path,
    phase: str,
    status: str,
    summary: str,
    result_path: Path,
    artifact_paths: list[str],
    source: str,
    source_packet: str,
    override_reason: str,
) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")

    lines = [
        f"## {utc_now()} result",
        "",
        f"- Phase: `{phase}`",
        f"- Result status: `{status}`",
        f"- Summary: {summary}",
        f"- Source: `{source}`",
        f"- Result record: `{display_path(result_path)}`",
    ]
    if source_packet:
        lines.append(f"- Source packet: `{source_packet}`")
    if override_reason:
        lines.append(f"- Override reason: {override_reason}")
    if artifact_paths:
        lines.append(f"- Evidence artifacts: {', '.join(f'`{path}`' for path in artifact_paths)}")
    lines.append("")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


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
    debug_log(
        spec,
        "start",
        {
            "spec_path": str(spec_path),
            "phase_arg": args.phase or "",
            "status": args.status,
            "source": args.source,
            "no_rerun": args.no_rerun,
        },
    )

    phase = args.phase or current_phase_from_run_status(spec)
    results_dir = artifact_path(spec, "phase_results_dir")
    run_log_path = artifact_path(spec, "run_log_md")
    results_dir.mkdir(parents=True, exist_ok=True)
    base_dirs = [project_root(spec), spec_path.parent]

    source_packet_display = ""
    if args.source == "manual-override" and not args.override_reason:
        print("--override-reason is required when --source manual-override is used.", file=sys.stderr)
        return 1
    if args.source == "execution-packet":
        if not args.source_packet:
            print("--source-packet is required when --source execution-packet is used.", file=sys.stderr)
            return 1
        source_packet = resolve_existing_path(args.source_packet, base_dirs)
        if source_packet is None or not source_packet.is_dir():
            print(f"Execution packet not found: {args.source_packet}", file=sys.stderr)
            return 1
        source_packet_display = display_path(source_packet)

    notes = ""
    if args.notes_file:
        notes_path = resolve_existing_path(args.notes_file, base_dirs)
        if notes_path is None:
            print(f"Notes file not found: {args.notes_file}", file=sys.stderr)
            return 1
        notes = notes_path.read_text(encoding="utf-8").strip()

    resolved_artifacts: list[str] = []
    for raw_path in args.artifact_path:
        resolved = resolve_existing_path(raw_path, base_dirs)
        if resolved is None:
            print(f"Evidence artifact not found: {raw_path}", file=sys.stderr)
            return 1
        resolved_artifacts.append(display_path(resolved))

    status_slug = re.sub(r"[^a-z0-9]+", "-", args.status.lower()).strip("-") or "result"
    result_path = results_dir / f"{timestamp_slug()}-{phase}-{status_slug}.md"

    lines = [
        "# Phase Result",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Phase: `{phase}`",
        f"- Recorded: `{utc_now()}`",
        f"- Result status: `{args.status}`",
        f"- Summary: {args.summary}",
        f"- Source: `{args.source}`",
        "",
        "## Evidence Artifacts",
        "",
    ]
    if source_packet_display:
        lines.insert(8, f"- Source packet: `{source_packet_display}`")
    if args.override_reason:
        insert_at = 9 if source_packet_display else 8
        lines.insert(insert_at, f"- Override reason: {args.override_reason}")
    if resolved_artifacts:
        for artifact in resolved_artifacts:
            lines.append(f"- `{artifact}`")
    else:
        lines.append("- None recorded")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            notes or "No additional notes provided.",
            "",
            "## Follow Up",
            "",
            "- Update the relevant artifact status fields only when this execution materially advances the phase artifacts.",
            f"- Run `./scripts/supernb certify-phase --initiative-id {initiative_id} --phase {phase}` before any gate advance.",
            f"- Re-run `./scripts/supernb run --initiative-id {initiative_id}` after artifact and certification changes.",
        ]
    )
    result_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    append_to_run_log(
        run_log_path,
        phase,
        args.status,
        args.summary,
        result_path,
        resolved_artifacts,
        args.source,
        source_packet_display,
        args.override_reason or "",
    )
    debug_log(
        spec,
        "complete",
        {
            "initiative_id": initiative_id,
            "phase": phase,
            "status": args.status,
            "source": args.source,
            "result_path": display_path(result_path),
            "source_packet": source_packet_display,
            "evidence_artifact_count": len(resolved_artifacts),
            "no_rerun": args.no_rerun,
        },
    )

    print(f"Recorded phase result: {result_path}")
    if not args.no_rerun:
        subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--spec", str(spec_path)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
