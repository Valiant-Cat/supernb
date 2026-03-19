#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.supernb_common import (
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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record a supernb phase execution result and optionally re-evaluate the initiative.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", help="Phase name. Defaults to the current selected phase from run-status.json.")
    parser.add_argument("--status", required=True, help="Outcome label, e.g. succeeded, blocked, needs-follow-up, approved, verified")
    parser.add_argument("--summary", required=True, help="One-line execution summary")
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


def append_to_run_log(log_path: Path, phase: str, status: str, summary: str, result_path: Path, artifact_paths: list[str]) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")

    lines = [
        f"## {utc_now()} result",
        "",
        f"- Phase: `{phase}`",
        f"- Result status: `{status}`",
        f"- Summary: {summary}",
        f"- Result record: `{display_path(result_path)}`",
    ]
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

    phase = args.phase or current_phase_from_run_status(spec)
    results_dir = artifact_path(spec, "phase_results_dir")
    run_log_path = artifact_path(spec, "run_log_md")
    results_dir.mkdir(parents=True, exist_ok=True)
    base_dirs = [project_root(spec)]

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
        "",
        "## Evidence Artifacts",
        "",
    ]
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

    append_to_run_log(run_log_path, phase, args.status, args.summary, result_path, resolved_artifacts)

    print(f"Recorded phase result: {result_path}")
    if not args.no_rerun:
        subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--initiative-id", initiative_id], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
