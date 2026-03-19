#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
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
    phase_artifact_snapshot,
    phase_targets as common_phase_targets,
    project_root as common_project_root,
    resolve_spec_path as common_resolve_spec_path,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a phase gate status update and re-evaluate the initiative.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", required=True, choices=PHASES, help="Phase to advance")
    parser.add_argument("--status", required=True, help="Target gate status for the phase")
    parser.add_argument("--actor", default="supernb", help="Name to write into Approved by")
    parser.add_argument("--date", default=today_stamp(), help="Date to write into Approved on")
    parser.add_argument("--summary", help="Optional summary for the generated gate update record")
    parser.add_argument("--no-rerun", action="store_true", help="Do not invoke supernb run after applying the status")
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
    common_append_debug_log(spec, ROOT_DIR, "supernb-advance-phase", event, payload)


def replace_field(path: Path, field: str, value: str) -> None:
    pattern = re.compile(rf"^(- {re.escape(field)}:).*$", re.MULTILINE)
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(rf"\1 {value}", text, count=1)
    if count == 0:
        lines = text.splitlines()
        insert_at = 1 if lines else 0
        last_metadata_index = -1
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("## "):
                break
            if stripped.startswith("- ") and ":" in stripped:
                last_metadata_index = idx
        if last_metadata_index >= 0:
            insert_at = last_metadata_index + 1
        field_line = f"- {field}: {value}" if value else f"- {field}:"
        lines.insert(insert_at, field_line)
        updated = "\n".join(lines)
        if text.endswith("\n"):
            updated += "\n"
    path.write_text(updated, encoding="utf-8")


def phase_targets(spec: dict[str, Any], phase: str) -> list[Path]:
    return common_phase_targets(spec, phase, ROOT_DIR)


def ensure_certification_gate(spec: dict[str, Any], phase: str, status: str) -> None:
    normalized = status.strip().lower()
    if normalized == "pending":
        return
    state = load_certification_state(certification_state_path(spec))
    entry = state.get("phases", {}).get(phase)
    current_snapshot = phase_artifact_snapshot(spec, phase, ROOT_DIR, DISPLAY_ROOTS)
    if certification_passed(entry, normalized) and certification_snapshot_matches(entry, current_snapshot):
        return
    report_path = ""
    if isinstance(entry, dict):
        report_path = str(entry.get("report_path", "")).strip()
    message = [f"Cannot advance {phase} to {normalized} without a passing and current certification result."]
    if report_path:
        message.append(f"Latest certification report: {report_path}")
    else:
        message.append(f"Run ./scripts/supernb certify-phase --initiative-id {nested_get(spec, 'initiative', 'id')} --phase {phase} first.")
    raise ValueError(" ".join(message))


def phase_update_spec(phase: str, status: str, actor: str, date_value: str) -> list[tuple[str, str]]:
    normalized = status.strip().lower()
    if phase == "research":
        if normalized not in {"approved", "pending"}:
            raise ValueError("research supports statuses: approved, pending")
        return [
            ("Status", normalized),
            ("Approved by", actor if normalized == "approved" else ""),
            ("Approved on", date_value if normalized == "approved" else ""),
        ]
    if phase == "prd":
        if normalized not in {"approved", "pending"}:
            raise ValueError("prd supports statuses: approved, pending")
        return [
            ("Approval status", normalized),
            ("Approved by", actor if normalized == "approved" else ""),
            ("Approved on", date_value if normalized == "approved" else ""),
        ]
    if phase == "design":
        if normalized not in {"approved", "pending"}:
            raise ValueError("design supports statuses: approved, pending")
        return [
            ("Approval status", normalized),
            ("Approved by", actor if normalized == "approved" else ""),
            ("Approved on", date_value if normalized == "approved" else ""),
        ]
    if phase == "planning":
        if normalized not in {"ready", "pending"}:
            raise ValueError("planning supports statuses: ready, pending")
        return [
            ("Ready for execution", "yes" if normalized == "ready" else "no"),
            ("Approved by", actor if normalized == "ready" else ""),
            ("Approved on", date_value if normalized == "ready" else ""),
        ]
    if phase == "delivery":
        if normalized not in {"verified", "pending"}:
            raise ValueError("delivery supports statuses: verified, pending")
        return [
            ("Delivery status", normalized),
            ("Approved by", actor if normalized == "verified" else ""),
            ("Approved on", date_value if normalized == "verified" else ""),
        ]
    if normalized not in {"ready", "pending"}:
        raise ValueError("release supports statuses: ready, pending")
    return [
        ("Release decision", normalized),
        ("Approved by", actor if normalized == "ready" else ""),
        ("Approved on", date_value if normalized == "ready" else ""),
    ]


def append_run_log(log_path: Path, phase: str, status: str, actor: str, result_path: Path) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")
    lines = [
        f"## {utc_now()} gate-update",
        "",
        f"- Phase: `{phase}`",
        f"- Applied status: `{status}`",
        f"- Actor: `{actor}`",
        f"- Gate record: `{display_path(result_path)}`",
        "",
    ]
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
            "initiative_id": initiative_id,
            "phase": args.phase,
            "status": args.status,
            "actor": args.actor,
            "no_rerun": args.no_rerun,
        },
    )

    try:
        ensure_certification_gate(spec, args.phase, args.status)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    targets = phase_targets(spec, args.phase)
    updates = phase_update_spec(args.phase, args.status, args.actor, args.date)
    for target in targets:
        if not target.is_file():
            raise FileNotFoundError(f"Artifact not found for phase {args.phase}: {target}")
        for field, value in updates:
            replace_field(target, field, value)

    results_dir = artifact_path(spec, "phase_results_dir")
    run_log_path = artifact_path(spec, "run_log_md")
    results_dir.mkdir(parents=True, exist_ok=True)

    result_path = results_dir / f"{timestamp_slug()}-{args.phase}-gate-{args.status.lower()}.md"
    summary = args.summary or f"Applied {args.phase} gate status '{args.status}'."
    lines = [
        "# Phase Gate Update",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Phase: `{args.phase}`",
        f"- Applied status: `{args.status}`",
        f"- Actor: `{args.actor}`",
        f"- Applied on: `{args.date}`",
        f"- Recorded: `{utc_now()}`",
        f"- Summary: {summary}",
        "",
        "## Updated Artifacts",
        "",
    ]
    for target in targets:
        lines.append(f"- `{display_path(target)}`")
    lines.extend(["", "## Updated Fields", ""])
    for field, value in updates:
        lines.append(f"- `{field}` => `{value}`")
    result_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    append_run_log(run_log_path, args.phase, args.status, args.actor, result_path)
    debug_log(
        spec,
        "complete",
        {
            "initiative_id": initiative_id,
            "phase": args.phase,
            "status": args.status,
            "actor": args.actor,
            "result_path": display_path(result_path),
            "targets": [display_path(target) for target in targets],
            "no_rerun": args.no_rerun,
        },
    )

    print(f"Applied phase status: {args.phase} -> {args.status}")
    print(f"Gate update record: {result_path}")

    if not args.no_rerun:
        subprocess.run(
            [
                sys.executable,
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(spec_path),
            ],
            check=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
