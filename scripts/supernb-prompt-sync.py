#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from lib.supernb_common import (
    PHASES,
    assert_ralph_loop_environment,
    append_debug_log,
    artifact_path,
    debug_log_dir,
    display_path,
    load_spec,
    nested_get,
    project_root,
    resolve_spec_path,
    supernb_cli_prefix,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
RALPH_LOOP_PLUGIN_ROOT = ROOT_DIR / "bundles" / "claude-loop-marketplace" / "supernb-loop"
RALPH_LOOP_SETUP_SCRIPT = RALPH_LOOP_PLUGIN_ROOT / "scripts" / "setup-superpower-loop.sh"
RALPH_LOOP_AUDIT_WATCHER = ROOT_DIR / "scripts" / "supernb-loop-audit-watcher.py"
SUPERNB_WRAPPER = ROOT_DIR / "scripts" / "supernb"
EXECUTE_NEXT_SCRIPT = ROOT_DIR / "scripts" / "supernb-execute-next.py"
LOOP_PHASE_SETTINGS = {
    "planning": {"required": True, "max_iterations": 6},
    "delivery": {"required": True, "max_iterations": 8},
    "design": {"required": False, "max_iterations": 4},
}

REPORT_TEMPLATE = {
    "completion_status": "completed",
    "summary": "",
    "completed_items": [],
    "remaining_items": [],
    "evidence_artifacts": [],
    "artifacts_updated": [],
    "commands_run": [],
    "tests_run": [],
    "validated_batches_completed": 0,
    "batch_commits": [],
    "workflow_trace": {
        "brainstorming": {"used": False, "evidence": ""},
        "writing_plans": {"used": False, "evidence": ""},
        "test_driven_development": {"used": False, "evidence": ""},
        "code_review": {"used": False, "evidence": ""},
        "using_git_worktrees": {"used": False, "evidence": ""},
        "subagent_or_executing_plans": {"used": False, "evidence": ""},
    },
    "loop_execution": {
        "used": False,
        "mode": "none",
        "completion_promise": "",
        "state_file": "",
        "max_iterations": 0,
        "final_iteration": 0,
        "exit_reason": "",
        "evidence": "",
    },
    "recommended_result_status": "needs-follow-up",
    "recommended_gate_action": "certify",
    "recommended_gate_status": "",
    "follow_up": [],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh initiative state for prompt-first supernb use and emit a prompt session contract.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument(
        "--project-dir",
        help="Optional product project root used when auto-discovering the initiative from a repo without passing --initiative-id.",
    )
    parser.add_argument("--phase", choices=["auto", *PHASES], default="auto", help="Optional phase override forwarded to supernb run")
    parser.add_argument("--no-run", action="store_true", help="Do not refresh run-status before generating the prompt session files")
    parser.add_argument(
        "--start-loop",
        action="store_true",
        help="When the selected phase requires Ralph Loop, start it immediately in the current Claude Code session after writing the prompt session files.",
    )
    parser.add_argument(
        "--direct-bridge-fallback",
        action="store_true",
        help="If Ralph Loop cannot bind to the current Claude session, fall back to direct `execute-next --harness claude-code` for loop-required phases.",
    )
    return parser.parse_args()


def discover_spec(project_dir: Path) -> Path:
    candidates = sorted((project_dir / ".supernb" / "initiatives").glob("*/initiative.yaml"))
    if not candidates:
        raise FileNotFoundError(
            f"No initiative.yaml found under {project_dir / '.supernb' / 'initiatives'}. "
            "Create an initiative first or pass --initiative-id/--spec."
        )
    if len(candidates) == 1:
        return candidates[0].resolve()

    def sort_key(path: Path) -> tuple[float, str]:
        run_status = path.parent / "run-status.json"
        timestamp = run_status.stat().st_mtime if run_status.exists() else path.stat().st_mtime
        return (timestamp, str(path))

    candidates.sort(key=sort_key, reverse=True)
    return candidates[0].resolve()


def resolve_spec_path_local(args: argparse.Namespace) -> Path:
    if args.spec or args.initiative_id:
        return resolve_spec_path(args, ROOT_DIR)
    project_dir = Path(args.project_dir).expanduser().resolve() if args.project_dir else Path.cwd().resolve()
    return discover_spec(project_dir)


def latest_execution_packet(spec: dict[str, Any], phase: str) -> Path | None:
    executions_dir = artifact_path(spec, "executions_dir", ROOT_DIR)
    if not executions_dir.is_dir():
        return None
    candidates = sorted(
        [path for path in executions_dir.iterdir() if path.is_dir() and f"-{phase}-" in path.name],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "initiative"


def loop_settings(initiative_id: str, phase: str, project_dir: Path, initiative_root: Path) -> dict[str, Any]:
    phase_settings = LOOP_PHASE_SETTINGS.get(phase, {"required": False, "max_iterations": 4})
    slug = slugify(f"{initiative_id}-{phase}")
    completion_promise = f"SUPERNB {initiative_id} {phase} batch complete"
    state_file = project_dir / ".claude" / f"superpower-loop-{slug}.local.md"
    prompt_file = initiative_root / f"ralph-loop-{phase}.md"
    manifest_file = initiative_root / f"ralph-loop-{phase}.json"
    audit_summary_file = initiative_root / f"ralph-loop-{phase}-audit.json"
    audit_events_file = initiative_root / f"ralph-loop-{phase}-audit.ndjson"
    start_command = [
        "bash",
        str(RALPH_LOOP_SETUP_SCRIPT),
        "--prompt-file",
        str(prompt_file),
        "--completion-promise",
        completion_promise,
        "--max-iterations",
        str(phase_settings["max_iterations"]),
        "--state-file",
        str(state_file),
    ]
    return {
        "required": bool(phase_settings["required"]),
        "max_iterations": int(phase_settings["max_iterations"]),
        "completion_promise": completion_promise,
        "state_file": state_file,
        "prompt_file": prompt_file,
        "manifest_file": manifest_file,
        "audit_summary_file": audit_summary_file,
        "audit_events_file": audit_events_file,
        "setup_script": RALPH_LOOP_SETUP_SCRIPT,
        "start_command": start_command,
        "start_command_text": shlex.join(start_command),
    }


def write_report_template(target: Path, phase: str, loop_config: dict[str, Any]) -> None:
    payload = dict(REPORT_TEMPLATE)
    payload["workflow_trace"] = dict(REPORT_TEMPLATE["workflow_trace"])
    payload["loop_execution"] = dict(REPORT_TEMPLATE["loop_execution"])
    payload["summary"] = f"{phase} phase prompt-first execution summary"
    if phase == "planning":
        payload["workflow_trace"]["writing_plans"] = {"used": True, "evidence": "Updated implementation plan and planning artifacts."}
    if phase == "delivery":
        payload["workflow_trace"]["writing_plans"] = {"used": True, "evidence": "Kept implementation plan and release artifacts aligned with the delivery batch."}
        payload["workflow_trace"]["test_driven_development"] = {"used": True, "evidence": "Ran delivery verification before finalizing the batch."}
        payload["workflow_trace"]["code_review"] = {"used": True, "evidence": "Reviewed the completed batch before final summary."}
        payload["workflow_trace"]["subagent_or_executing_plans"] = {"used": True, "evidence": "Executed one bounded delivery batch against the current plan."}
    if loop_config["required"]:
        payload["evidence_artifacts"] = [str(loop_config["audit_summary_file"])]
        payload["loop_execution"] = {
            "used": True,
            "mode": "ralph-loop",
            "completion_promise": loop_config["completion_promise"],
            "state_file": str(loop_config["state_file"]),
            "max_iterations": loop_config["max_iterations"],
            "final_iteration": 0,
            "exit_reason": "",
            "evidence": str(loop_config["audit_summary_file"]),
        }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_loop_prompt(
    target: Path,
    spec: dict[str, Any],
    spec_path: Path,
    selected_phase: str,
    run_status: dict[str, Any],
    report_template_path: Path,
    loop_config: dict[str, Any],
) -> None:
    supernb_command = str(SUPERNB_WRAPPER)
    import_command = shlex.join(
        [
            supernb_command,
            "import-execution",
            "--spec",
            str(spec_path),
            "--phase",
            selected_phase,
            "--report-json",
            str(report_template_path),
            "--harness",
            "claude-code-prompt",
        ]
    )
    apply_command = shlex.join(
        [
            supernb_command,
            "apply-execution",
            "--spec",
            str(spec_path),
            "--packet",
            "<latest-imported-packet>",
            "--apply-certification" if loop_config["required"] else "--certify",
        ]
    )
    closeout_command = shlex.join(
        [
            supernb_command,
            "prompt-closeout",
            "--spec",
            str(spec_path),
            "--phase",
            selected_phase,
            "--report-json",
            str(report_template_path),
        ]
    )
    next_command = run_status.get("next_command") or {}
    next_command_path = str(next_command.get("path", "")).strip()
    lines = [
        f"Use supernb to complete the current {selected_phase} phase batch for initiative `{nested_get(spec, 'initiative', 'id')}`.",
        "",
        "Mandatory rules:",
        "- Do not stop because you feel done. Keep iterating until the completion promise is actually true.",
        "- This loop depends on a Claude Code environment where the Ralph Loop stop-hook is enabled.",
        "- Work only inside the current phase scope and current batch boundaries.",
        "- Update affected initiative artifacts, tests, evidence, and git state as part of the batch.",
        "- Before stopping, fill the prompt report template with real evidence, then run the managed prompt closeout command so supernb imports it, applies certification, and only then emits the final promise when allowed.",
        "- If the stop-hook is unavailable in this Claude environment, do not pretend the batch is cleanly complete. Report the run as needs-follow-up and switch to a loop-enabled Claude environment.",
        "",
        f"Spec: {spec_path}",
        f"Run status: {artifact_path(spec, 'run_status_json', ROOT_DIR)}",
        f"Phase packet: {artifact_path(spec, 'phase_packet_md', ROOT_DIR)}",
    ]
    if next_command_path:
        lines.append(f"Next command: {next_command_path}")
    lines.extend(
        [
            f"Prompt report template: {report_template_path}",
            "",
            "Completion criteria:",
            "- The current batch is implemented to the claimed depth.",
            "- Verification and review evidence are real and recorded.",
            "- The prompt report template contains real commands, tests, evidence artifacts, workflow trace, loop evidence, and commit information.",
            f"- `{closeout_command}` has completed successfully for this prompt-first batch.",
            "",
            "Required closeout commands:",
            f"- Managed closeout: {closeout_command}",
            f"- Under the hood this runs: {import_command}",
            f"- Then it runs: {apply_command}",
            "",
            "Do not type the final promise manually.",
            "Only after the managed closeout command succeeds may you echo the exact promise line that it prints.",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_loop_manifest(target: Path, phase: str, loop_config: dict[str, Any]) -> None:
    payload = {
        "phase": phase,
        "required": loop_config["required"],
        "mode": "ralph-loop" if loop_config["required"] else "optional",
        "stop_hook_required": loop_config["required"],
        "stop_hook_provider": "supernb-loop stop-hook",
        "completion_promise": loop_config["completion_promise"],
        "state_file": str(loop_config["state_file"]),
        "prompt_file": str(loop_config["prompt_file"]),
        "audit_summary_file": str(loop_config["audit_summary_file"]),
        "audit_events_file": str(loop_config["audit_events_file"]),
        "setup_script": str(loop_config["setup_script"]),
        "max_iterations": loop_config["max_iterations"],
        "start_command": loop_config["start_command"],
        "start_command_text": loop_config["start_command_text"],
    }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_prompt_session(
    session_path: Path,
    spec: dict[str, Any],
    spec_path: Path,
    run_status_path: Path,
    run_status: dict[str, Any],
    latest_packet: Path | None,
    report_template_path: Path,
    loop_config: dict[str, Any],
) -> None:
    supernb_command = str(SUPERNB_WRAPPER)
    initiative_id = nested_get(spec, "initiative", "id")
    selected_phase = str(run_status.get("selected_phase", "")).strip()
    auto_start_command = shlex.join([supernb_command, "prompt-bootstrap", "--spec", str(spec_path), "--start-loop"])
    import_command = shlex.join(
        [
            supernb_command,
            "import-execution",
            "--spec",
            str(spec_path),
            "--phase",
            selected_phase,
            "--report-json",
            str(report_template_path),
            "--harness",
            "claude-code-prompt",
        ]
    )
    apply_command = shlex.join(
        [
            supernb_command,
            "apply-execution",
            "--spec",
            str(spec_path),
            "--packet",
            "<latest-imported-packet>",
            "--apply-certification" if loop_config["required"] else "--certify",
        ]
    )
    closeout_command = shlex.join(
        [
            supernb_command,
            "prompt-closeout",
            "--spec",
            str(spec_path),
            "--phase",
            selected_phase,
            "--report-json",
            str(report_template_path),
        ]
    )
    next_command = run_status.get("next_command") or {}
    next_command_path = str(next_command.get("path", "")).strip()
    lines = [
        "# Prompt Session Contract",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Spec: `{spec_path}`",
        f"- Project dir: `{project_root(spec, ROOT_DIR)}`",
        f"- Run status: `{run_status_path}`",
        f"- Active phase: `{selected_phase}`",
        f"- Debug logs dir: `{debug_log_dir(spec, ROOT_DIR)}`",
        "",
        "## Mandatory Prompt-First Workflow",
        "",
        "1. Read the active `next-command.md`, `phase-packet.md`, and any active phase artifacts before making changes.",
        "2. Implement only the current phase scope. Do not silently skip or jump phases.",
        "3. If you change code or initiative artifacts, keep tests, review notes, and git state aligned with the claimed batch.",
        "4. Before finishing, write the report template with concrete evidence and then import+apply it so the initiative state stays in sync.",
        "",
        "## Required Files",
        "",
    ]
    if next_command_path:
        lines.append(f"- Next command: `{next_command_path}`")
    lines.append(f"- Phase packet: `{display_path(artifact_path(spec, 'phase_packet_md', ROOT_DIR), [project_root(spec, ROOT_DIR), ROOT_DIR])}`")
    lines.append(f"- Report template: `{report_template_path}`")
    if latest_packet is not None:
        lines.append(
            f"- Latest execution packet for this phase: `{display_path(latest_packet, [project_root(spec, ROOT_DIR), ROOT_DIR])}`"
        )
    if loop_config["required"]:
        lines.extend(
            [
                "",
                "## Ralph Loop Requirement",
                "",
                f"- Required for this phase: `yes`",
            f"- Loop prompt file: `{loop_config['prompt_file']}`",
            f"- Loop manifest: `{loop_config['manifest_file']}`",
                f"- Completion promise: `{loop_config['completion_promise']}`",
                f"- State file: `{loop_config['state_file']}`",
                f"- Max iterations: `{loop_config['max_iterations']}`",
                f"- Loop audit summary: `{loop_config['audit_summary_file']}`",
                f"- Loop audit events: `{loop_config['audit_events_file']}`",
                f"- Managed auto-start command: `{auto_start_command}`",
                f"- Start command: `{loop_config['start_command_text']}`",
                f"- Managed closeout command: `{closeout_command}`",
                "- Claude Code must have the managed supernb Ralph Loop stop-hook enabled for this contract to be enforceable.",
                "- Do not let the agent stop on self-judgment alone. The Ralph Loop completion promise must only be echoed after the managed closeout command succeeds.",
            ]
        )
    lines.extend(
        [
            "",
            "## Closeout Commands For The Agent",
            "",
            f"- Managed closeout: `{closeout_command}`",
            f"- Import structured prompt report: `{import_command}`",
            f"- Apply imported packet: `{apply_command}`",
            "",
            "## Notes",
            "",
            "- For planning and delivery, managed closeout requires `--apply-certification`; if certification fails, the session must keep working instead of emitting the completion promise.",
            "- Do not claim completion without updating the report template with real commands, tests, evidence artifacts, and workflow trace.",
        ]
    )
    session_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def wait_for_loop_audit_observed(loop_config: dict[str, Any], timeout_seconds: float = 4.0) -> dict[str, Any] | None:
    summary_path = Path(loop_config["audit_summary_file"]).resolve()
    deadline = time.time() + max(timeout_seconds, 0.5)
    while time.time() < deadline:
        if summary_path.is_file():
            try:
                payload = json.loads(summary_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and payload.get("state_observed"):
                return payload
        time.sleep(0.1)
    if summary_path.is_file():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload
    return None


def parse_execute_next_summary(stdout: str) -> dict[str, str]:
    fields = {
        "initiative_id": "",
        "phase": "",
        "harness": "",
        "project_dir": "",
        "packet_dir": "",
        "summary_path": "",
        "response_path": "",
        "result_suggestion_path": "",
        "phase_readiness_path": "",
        "status": "",
    }
    prefix_map = {
        "Initiative: ": "initiative_id",
        "Phase: ": "phase",
        "Harness: ": "harness",
        "Project dir: ": "project_dir",
        "Execution packet: ": "packet_dir",
        "Summary: ": "summary_path",
        "Response: ": "response_path",
        "Result suggestion: ": "result_suggestion_path",
        "Phase readiness: ": "phase_readiness_path",
        "Status: ": "status",
    }
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        for prefix, key in prefix_map.items():
            if line.startswith(prefix):
                fields[key] = line.split(prefix, 1)[1].strip()
                break
    return fields


def write_direct_bridge_handoff(
    initiative_root: Path,
    phase: str,
    execute_next_summary: dict[str, str],
    proc: subprocess.CompletedProcess[str],
) -> tuple[Path, Path]:
    json_path = initiative_root / f"direct-bridge-handoff-{phase}.json"
    md_path = initiative_root / f"direct-bridge-handoff-{phase}.md"
    completed = proc.returncode == 0
    resume_summary = (
        "Direct bridge run finished. The current Claude session may exit observer mode."
        if completed
        else "Direct bridge run finished with blockers. The current Claude session may exit observer mode."
    )
    resume_next_step = (
        "Review the handoff artifact and continue from the current Claude session using the recorded packet and readiness outputs."
        if completed
        else "Review the handoff artifact and direct bridge output before continuing from the current Claude session."
    )
    payload = {
        "phase": phase,
        "status": "completed" if completed else "failed",
        "bridge_returncode": proc.returncode,
        "observer_mode_can_exit": True,
        "resume_summary": resume_summary,
        "resume_next_step": resume_next_step,
        "initiative_id": execute_next_summary.get("initiative_id", ""),
        "harness": execute_next_summary.get("harness", "claude-code"),
        "project_dir": execute_next_summary.get("project_dir", ""),
        "packet_dir": execute_next_summary.get("packet_dir", ""),
        "summary_path": execute_next_summary.get("summary_path", ""),
        "response_path": execute_next_summary.get("response_path", ""),
        "result_suggestion_path": execute_next_summary.get("result_suggestion_path", ""),
        "phase_readiness_path": execute_next_summary.get("phase_readiness_path", ""),
        "direct_bridge_status": execute_next_summary.get("status", ""),
    }
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Direct Bridge Handoff",
        "",
        f"- Phase: `{phase}`",
        f"- Status: `{payload['status']}`",
        f"- Observer mode can exit: `{'yes' if payload['observer_mode_can_exit'] else 'no'}`",
        f"- Resume summary: {resume_summary}",
        f"- Next step: {resume_next_step}",
    ]
    if payload["packet_dir"]:
        lines.append(f"- Execution packet: `{payload['packet_dir']}`")
    if payload["result_suggestion_path"]:
        lines.append(f"- Result suggestion: `{payload['result_suggestion_path']}`")
    if payload["phase_readiness_path"]:
        lines.append(f"- Phase readiness: `{payload['phase_readiness_path']}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def run_direct_claude_bridge_fallback(spec: dict[str, Any], spec_path: Path, phase: str, cwd: Path, initiative_root: Path) -> int:
    command = [
        sys.executable,
        str(EXECUTE_NEXT_SCRIPT),
        "--spec",
        str(spec_path),
        "--phase",
        phase,
        "--harness",
        "claude-code",
    ]
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    print(
        "Direct bridge fallback activated because Ralph Loop could not bind to the current Claude session. "
        "Running execute-next with harness=claude-code."
    )
    print(
        "The current Claude session must switch to observer mode. "
        "Do not continue editing or committing in parallel while the direct bridge run is active."
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    execute_next_summary = parse_execute_next_summary(proc.stdout or "")
    handoff_json, handoff_md = write_direct_bridge_handoff(initiative_root, phase, execute_next_summary, proc)
    print(
        "Direct bridge run finished. The current Claude session may exit observer mode."
        if proc.returncode == 0
        else "Direct bridge run finished with blockers. The current Claude session may exit observer mode."
    )
    print(f"Bridge handoff: {handoff_json}")
    print(f"Bridge handoff summary: {handoff_md}")
    print(
        "Next step: review the handoff and continue from the current Claude session."
        if proc.returncode == 0
        else "Next step: inspect the handoff and direct bridge output before continuing from the current Claude session."
    )
    append_debug_log(
        spec,
        ROOT_DIR,
        "supernb-prompt-sync",
        "direct-bridge-fallback-complete",
        {
            "spec_path": str(spec_path),
            "phase": phase,
            "returncode": proc.returncode,
            "handoff_json": str(handoff_json),
            "handoff_md": str(handoff_md),
            "packet_dir": execute_next_summary.get("packet_dir", ""),
            "result_suggestion_path": execute_next_summary.get("result_suggestion_path", ""),
            "phase_readiness_path": execute_next_summary.get("phase_readiness_path", ""),
        },
    )
    return proc.returncode


def start_loop_in_current_session(spec: dict[str, Any], loop_config: dict[str, Any]) -> tuple[bool, str]:
    if not loop_config["required"]:
        return False, "selected phase does not require Ralph Loop"

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if not session_id:
        raise RuntimeError(
            "CLAUDE_CODE_SESSION_ID is not set. "
            "Run --start-loop from inside the active Claude Code session so the loop state file is bound to that session. "
            f"If you only need the prompt files, rerun without --start-loop, for example: "
            f"`{supernb_cli_prefix(ROOT_DIR)} prompt-sync --spec <initiative.yaml> --no-run`."
        )

    project_dir = project_root(spec, ROOT_DIR)
    plugin_metadata = assert_ralph_loop_environment(project_dir)

    setup_script = Path(loop_config["setup_script"]).resolve()
    if not setup_script.is_file():
        raise FileNotFoundError(f"Ralph Loop setup script not found: {setup_script}")
    if not RALPH_LOOP_AUDIT_WATCHER.is_file():
        raise FileNotFoundError(f"Ralph Loop audit watcher not found: {RALPH_LOOP_AUDIT_WATCHER}")
    proc = subprocess.run(
        loop_config["start_command"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"Failed to start Ralph Loop: {stderr}")

    state_file = Path(loop_config["state_file"]).resolve()
    if not state_file.is_file():
        raise RuntimeError(f"Ralph Loop setup completed without creating the state file: {state_file}")

    subprocess.Popen(
        [
            sys.executable,
            str(RALPH_LOOP_AUDIT_WATCHER),
            "--state-file",
            str(loop_config["state_file"]),
            "--summary-json",
            str(loop_config["audit_summary_file"]),
            "--events-ndjson",
            str(loop_config["audit_events_file"]),
            "--completion-promise",
            loop_config["completion_promise"],
            "--max-iterations",
            str(loop_config["max_iterations"]),
            "--expected-session-id",
            session_id,
        ],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    observed_payload = wait_for_loop_audit_observed(loop_config)
    if not observed_payload or not observed_payload.get("state_observed"):
        raise RuntimeError(
            "Ralph Loop audit watcher did not confirm the state file after startup. "
            "Do not treat this Claude session as loop-enforced until the audit summary records `state_observed: true`."
        )

    plugin_id = plugin_metadata.get("id", "")
    return True, f"{plugin_id} | {proc.stdout.strip()}"


def main() -> int:
    args = parse_args()
    try:
        spec_path = resolve_spec_path_local(args)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not spec_path.is_file():
        print(f"Initiative spec not found: {spec_path}", file=sys.stderr)
        return 1

    if not args.no_run:
        command = [sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--spec", str(spec_path)]
        if args.phase != "auto":
            command.extend(["--phase", args.phase])
        proc = subprocess.run(command, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            return proc.returncode

    spec = load_spec(spec_path)
    initiative_id = nested_get(spec, "initiative", "id")
    run_status_json = artifact_path(spec, "run_status_json", ROOT_DIR)
    if not run_status_json.is_file():
        print(f"Run status JSON not found after prompt sync: {run_status_json}", file=sys.stderr)
        return 1
    run_status = json.loads(run_status_json.read_text(encoding="utf-8"))
    selected_phase = str(run_status.get("selected_phase", "")).strip()
    if not selected_phase:
        print(f"selected_phase missing in {run_status_json}", file=sys.stderr)
        return 1

    initiative_root = spec_path.parent
    prompt_session_path = initiative_root / "prompt-session.md"
    report_template_path = initiative_root / "prompt-report-template.json"
    loop_config = loop_settings(initiative_id, selected_phase, project_root(spec, ROOT_DIR), initiative_root)
    write_report_template(report_template_path, selected_phase, loop_config)
    write_loop_prompt(loop_config["prompt_file"], spec, spec_path, selected_phase, run_status, report_template_path, loop_config)
    write_loop_manifest(loop_config["manifest_file"], selected_phase, loop_config)
    latest_packet = latest_execution_packet(spec, selected_phase)
    write_prompt_session(prompt_session_path, spec, spec_path, run_status_json, run_status, latest_packet, report_template_path, loop_config)
    loop_started = False
    loop_start_summary = ""
    if args.start_loop:
        try:
            loop_started, loop_start_summary = start_loop_in_current_session(spec, loop_config)
        except (FileNotFoundError, RuntimeError) as exc:
            if args.direct_bridge_fallback and loop_config["required"]:
                return run_direct_claude_bridge_fallback(spec, spec_path, selected_phase, project_root(spec, ROOT_DIR), initiative_root)
            print(str(exc), file=sys.stderr)
            return 1

    append_debug_log(
        spec,
        ROOT_DIR,
        "supernb-prompt-sync",
        "complete",
        {
            "initiative_id": initiative_id,
            "spec_path": str(spec_path),
            "selected_phase": selected_phase,
            "run_status_json": display_path(run_status_json, [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "prompt_session": display_path(prompt_session_path, [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "report_template": display_path(report_template_path, [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "loop_prompt": display_path(loop_config["prompt_file"], [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "loop_manifest": display_path(loop_config["manifest_file"], [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "loop_required": loop_config["required"],
            "loop_completion_promise": loop_config["completion_promise"],
            "loop_audit_summary": display_path(loop_config["audit_summary_file"], [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "loop_audit_events": display_path(loop_config["audit_events_file"], [project_root(spec, ROOT_DIR), ROOT_DIR]),
            "loop_started": loop_started,
            "loop_state_file": str(loop_config["state_file"]) if loop_started else "",
            "loop_start_summary": loop_start_summary,
            "claude_code_session_bound": bool(os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()),
            "latest_execution_packet": display_path(latest_packet, [project_root(spec, ROOT_DIR), ROOT_DIR]) if latest_packet else "",
            "ran_control_plane": not args.no_run,
        },
    )

    print(f"Initiative: {initiative_id}")
    print(f"Spec: {spec_path}")
    print(f"Selected phase: {selected_phase}")
    print(f"Prompt session: {prompt_session_path}")
    print(f"Report template: {report_template_path}")
    print(f"Ralph Loop prompt: {loop_config['prompt_file']}")
    print(f"Ralph Loop manifest: {loop_config['manifest_file']}")
    if args.start_loop:
        if loop_started:
            print(f"Ralph Loop started in current Claude session: {loop_config['state_file']}")
        else:
            print(f"Ralph Loop start skipped: {loop_start_summary}")
    if latest_packet is not None:
        print(f"Latest execution packet: {latest_packet}")
    else:
        print("Latest execution packet: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
