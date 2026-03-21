#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.supernb_common import (
    PHASES,
    append_debug_log,
    artifact_path,
    load_spec,
    nested_get,
    prompt_first_reassessment_blocker,
    prompt_first_reassessment_path,
    resolve_spec_path,
    supernb_cli_prefix,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
LOOP_REQUIRED_PHASES = {"planning", "delivery"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close out a prompt-first supernb session by importing the structured report, applying it, and only then emitting the Ralph Loop completion promise when applicable."
    )
    parser.add_argument("--initiative-id", help="Existing initiative id")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", choices=PHASES, help="Phase to close out. Defaults to the current selected phase.")
    parser.add_argument("--report-json", help="Structured prompt report JSON. Defaults to the initiative prompt-report-template.json.")
    parser.add_argument("--response-file", help="Optional response file to forward to import-execution")
    parser.add_argument("--stdout-file", help="Optional stdout log to forward to import-execution")
    parser.add_argument("--stderr-file", help="Optional stderr log to forward to import-execution")
    parser.add_argument("--artifact-path", action="append", default=[], help="Repeatable extra evidence artifact path")
    parser.add_argument("--actor", default="supernb", help="Actor used when apply-certification is required")
    parser.add_argument("--harness", default="claude-code-prompt", help="Harness label recorded by import-execution")
    return parser.parse_args()


def current_phase_from_run_status(spec: dict[str, Any]) -> str:
    run_status_json = artifact_path(spec, "run_status_json", ROOT_DIR)
    if not run_status_json.is_file():
        raise FileNotFoundError(f"Run status JSON not found: {run_status_json}")
    payload = json.loads(run_status_json.read_text(encoding="utf-8"))
    phase = str(payload.get("selected_phase", "")).strip()
    if not phase:
        raise ValueError(f"selected_phase missing in {run_status_json}")
    return phase


def default_report_json(spec: dict[str, Any]) -> Path:
    return artifact_path(spec, "run_status_md", ROOT_DIR).parent / "prompt-report-template.json"


def default_reassessment_path(spec: dict[str, Any]) -> Path:
    return prompt_first_reassessment_path(spec, ROOT_DIR)


def validate_reassessment(spec: dict[str, Any], spec_path: Path, phase: str) -> str | None:
    blocker = prompt_first_reassessment_blocker(spec, ROOT_DIR, spec_path, phase)
    if blocker is None:
        return None
    return blocker.replace("Prompt-first execution", "Prompt closeout", 1).replace("continue cleanly", "close out cleanly", 1)


def parse_execution_packet(stdout: str) -> Path:
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if line.startswith("Execution packet: "):
            return Path(line.split("Execution packet: ", 1)[1].strip()).expanduser().resolve()
    raise RuntimeError("Could not determine imported execution packet path from import-execution output.")


def loop_completion_promise(spec: dict[str, Any], phase: str) -> str:
    manifest_path = artifact_path(spec, "run_status_md", ROOT_DIR).parent / f"ralph-loop-{phase}.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Ralph Loop manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    promise = str(payload.get("completion_promise", "")).strip()
    if not promise:
        raise ValueError(f"completion_promise missing in {manifest_path}")
    return promise


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
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    try:
        phase = args.phase or current_phase_from_run_status(spec)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report_json = Path(args.report_json).expanduser().resolve() if args.report_json else default_report_json(spec)
    if not report_json.is_file():
        print(f"Prompt report JSON not found: {report_json}", file=sys.stderr)
        return 1

    reassessment_error = validate_reassessment(spec, spec_path, phase)
    if reassessment_error:
        print(reassessment_error, file=sys.stderr)
        append_debug_log(
            spec,
            ROOT_DIR,
            "supernb-prompt-closeout",
            "reassessment-blocked",
            {
                "initiative_id": initiative_id,
                "phase": phase,
                "report_json": str(report_json),
                "reassessment_path": str(default_reassessment_path(spec)),
            },
        )
        return 1

    append_debug_log(
        spec,
        ROOT_DIR,
        "supernb-prompt-closeout",
        "start",
        {
            "initiative_id": initiative_id,
            "phase": phase,
            "spec_path": str(spec_path),
            "report_json": str(report_json),
            "harness": args.harness,
        },
    )

    import_command = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
        "--spec",
        str(spec_path),
        "--phase",
        phase,
        "--report-json",
        str(report_json),
        "--harness",
        args.harness,
    ]
    if args.response_file:
        import_command.extend(["--response-file", args.response_file])
    if args.stdout_file:
        import_command.extend(["--stdout-file", args.stdout_file])
    if args.stderr_file:
        import_command.extend(["--stderr-file", args.stderr_file])
    for artifact_path_value in args.artifact_path:
        import_command.extend(["--artifact-path", artifact_path_value])

    import_proc = subprocess.run(import_command, capture_output=True, text=True)
    if import_proc.returncode != 0:
        sys.stderr.write(import_proc.stderr or import_proc.stdout)
        return import_proc.returncode

    packet_dir = parse_execution_packet(import_proc.stdout)

    apply_command = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "supernb-apply-execution.py"),
        "--spec",
        str(spec_path),
        "--packet",
        str(packet_dir),
    ]
    if phase in LOOP_REQUIRED_PHASES:
        apply_command.extend(["--apply-certification", "--actor", args.actor])
    else:
        apply_command.append("--certify")

    apply_proc = subprocess.run(apply_command, capture_output=True, text=True)
    if apply_proc.returncode != 0:
        if phase in LOOP_REQUIRED_PHASES:
            sys.stderr.write(
                f"Prompt closeout did not emit the Ralph Loop completion promise for {phase} because result recording/certification failed.\n"
            )
        sys.stderr.write(f"Imported execution packet: {packet_dir}\n")
        sys.stderr.write(
            f"Next step: run `{supernb_cli_prefix(ROOT_DIR)} apply-execution --spec {spec_path} --packet {packet_dir} --certify` to inspect blockers, "
            "then rerun prompt-closeout after the packet can succeed.\n"
        )
        sys.stderr.write(apply_proc.stderr or apply_proc.stdout)
        append_debug_log(
            spec,
            ROOT_DIR,
            "supernb-prompt-closeout",
            "apply-failed",
            {
                "initiative_id": initiative_id,
                "phase": phase,
                "packet_dir": str(packet_dir),
                "returncode": apply_proc.returncode,
            },
        )
        return apply_proc.returncode

    append_debug_log(
        spec,
        ROOT_DIR,
        "supernb-prompt-closeout",
        "complete",
        {
            "initiative_id": initiative_id,
            "phase": phase,
            "packet_dir": str(packet_dir),
            "loop_required": phase in LOOP_REQUIRED_PHASES,
        },
    )

    sys.stdout.write(import_proc.stdout)
    sys.stdout.write(apply_proc.stdout)
    print(f"Prompt closeout packet: {packet_dir}")
    print(f"Prompt closeout phase: {phase}")
    if phase in LOOP_REQUIRED_PHASES:
        promise = loop_completion_promise(spec, phase)
        print("Prompt closeout status: clean phase-complete")
        print(f"<promise>{promise}</promise>")
    else:
        print("Prompt closeout status: recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
