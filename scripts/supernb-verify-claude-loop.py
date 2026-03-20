#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_module(name: str, relative_path: str):
    module_path = ROOT_DIR / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


execute_next = load_module("supernb_execute_next_verify", "scripts/supernb-execute-next.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real Claude CLI Ralph Loop smoke verification with the bundled dotclaude plugin."
    )
    parser.add_argument(
        "--workspace",
        help="Optional workspace directory to use for the verification run. Defaults to a new temporary directory.",
    )
    parser.add_argument(
        "--allow-live-run",
        action="store_true",
        help="Actually invoke the real `claude -p` command. This performs a live Claude run and is not enabled by default.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete the verification workspace after a successful run.",
    )
    parser.add_argument(
        "--observation-timeout-seconds",
        type=float,
        default=5.0,
        help="How long to wait for the audit watcher to observe the loop state file before launching Claude.",
    )
    parser.add_argument(
        "--audit-timeout-seconds",
        type=float,
        default=30.0,
        help="How long to wait for the audit watcher to record final loop completion evidence.",
    )
    return parser.parse_args()


def ensure_workspace(path_arg: str | None) -> tuple[Path, bool]:
    if path_arg:
        workspace = Path(path_arg).expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace, False
    return Path(tempfile.mkdtemp(prefix="supernb-claude-loop-verify-")).resolve(), True


def build_verification_prompt(state_file: Path, completion_promise: str) -> str:
    return textwrap.dedent(
        f"""\
        Ralph Loop verification task:

        1. Read the Ralph Loop state file at `{state_file}`.
        2. Inspect the YAML frontmatter field `iteration`.
        3. If `iteration` is less than `2`, respond with exactly one line:
           `iteration=<n> verification-not-complete`
           Do not include any `<promise>` tag in that first response.
        4. If `iteration` is `2` or greater, respond with exactly these two lines:
           `iteration=<n> verification-complete`
           `<promise>{completion_promise}</promise>`
        5. The `<promise>...</promise>` line must be the final line when iteration >= 2.
        """
    ).strip() + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def validation_findings(
    completion_promise: str,
    session_id: str,
    response_text: str,
    exit_code: int,
    audit_summary: dict[str, Any] | None,
) -> list[str]:
    issues: list[str] = []
    if exit_code != 0:
        issues.append(f"`claude -p` exited with code {exit_code}.")

    promise_text = execute_next.extract_promise_text(response_text)
    last_non_empty_line = ""
    for line in reversed(response_text.splitlines()):
        if line.strip():
            last_non_empty_line = line.strip()
            break
    if promise_text != completion_promise:
        issues.append(
            "Final Claude response did not end with the expected Ralph Loop completion promise. "
            f"Expected `{completion_promise}` but saw `{promise_text or 'missing'}`."
        )
    expected_promise_line = f"<promise>{completion_promise}</promise>"
    if last_non_empty_line != expected_promise_line:
        issues.append(
            "The Ralph Loop completion promise was not the final non-empty response line. "
            f"Expected `{expected_promise_line}` but saw `{last_non_empty_line or 'missing'}`."
        )

    if not isinstance(audit_summary, dict):
        issues.append("Loop audit summary was not produced.")
        return issues

    if not audit_summary.get("state_observed"):
        issues.append("Loop audit summary never observed the state file.")
    if not audit_summary.get("removed_after_observation"):
        issues.append("Loop audit summary did not confirm the state file was removed after observation.")
    if str(audit_summary.get("final_status", "")).strip() != "state_removed":
        issues.append(
            f"Loop audit summary final_status must be `state_removed`, found `{audit_summary.get('final_status', '')}`."
        )
    if str(audit_summary.get("expected_session_id", "")).strip() != session_id:
        issues.append("Loop audit summary expected_session_id did not match the generated Claude session id.")
    if str(audit_summary.get("last_session_id", "")).strip() != session_id:
        issues.append("Loop audit summary last_session_id did not match the generated Claude session id.")
    try:
        last_iteration = int(audit_summary.get("last_iteration", 0) or 0)
    except (TypeError, ValueError):
        last_iteration = 0
    if last_iteration < 2:
        issues.append(
            "Loop audit summary did not prove a second Ralph Loop iteration. "
            f"Expected `last_iteration >= 2` but found `{last_iteration}`."
        )
    return issues


def main() -> int:
    args = parse_args()
    if not args.allow_live_run:
        print(
            "Refusing to invoke a live Claude CLI run without --allow-live-run. "
            "This command is meant to prove the real Ralph Loop hook lifecycle.",
            file=sys.stderr,
        )
        return 2

    if not shutil.which("claude"):
        print("`claude` CLI is not installed or not on PATH.", file=sys.stderr)
        return 1

    workspace, created_tempdir = ensure_workspace(args.workspace)
    packet_dir = workspace / "packet"
    packet_dir.mkdir(parents=True, exist_ok=True)

    initiative_id = "claude-loop-verify"
    phase = "planning"
    response_path = packet_dir / "response.md"
    stdout_path = packet_dir / "stdout.log"
    stderr_path = packet_dir / "stderr.log"
    request_path = packet_dir / "request.json"
    result_path = packet_dir / "verification-result.json"

    loop_contract = execute_next.build_direct_loop_contract(initiative_id, phase, packet_dir, workspace)
    prompt_text = build_verification_prompt(Path(loop_contract["state_file"]), loop_contract["completion_promise"])
    write_text(Path(loop_contract["prompt_file"]), prompt_text)

    try:
        plugin_metadata = execute_next.start_direct_claude_loop(workspace, loop_contract)
        observed_payload = execute_next.wait_for_loop_state_observed(
            loop_contract,
            timeout_seconds=args.observation_timeout_seconds,
        )
        if not observed_payload or not observed_payload.get("state_observed"):
            raise RuntimeError(
                "The audit watcher did not confirm `state_observed: true` before the live Claude run started."
            )
    except (FileNotFoundError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    command = execute_next.build_execution_command("claude-code", workspace, response_path, [], loop_contract)
    write_json(
        request_path,
        {
            "workspace": str(workspace),
            "command": command,
            "ralph_loop": execute_next.serialize_loop_contract(loop_contract),
            "ralph_loop_plugin": plugin_metadata,
        },
    )

    run_env = dict(os.environ)
    run_env["CLAUDE_CODE_SESSION_ID"] = loop_contract["session_id"]
    proc = subprocess.run(
        command,
        input=prompt_text,
        text=True,
        capture_output=True,
        cwd=str(workspace),
        env=run_env,
    )

    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    response_path.write_text(proc.stdout, encoding="utf-8")

    audit_summary = execute_next.wait_for_loop_audit_summary(
        loop_contract,
        timeout_seconds=args.audit_timeout_seconds,
    )
    findings = validation_findings(
        loop_contract["completion_promise"],
        loop_contract["session_id"],
        proc.stdout,
        proc.returncode,
        audit_summary,
    )

    write_json(
        result_path,
        {
            "workspace": str(workspace),
            "success": not findings,
            "issues": findings,
            "exit_code": proc.returncode,
            "command": command,
            "ralph_loop": execute_next.serialize_loop_contract(loop_contract),
            "ralph_loop_plugin": plugin_metadata,
            "audit_summary": audit_summary or {},
            "response_path": str(response_path),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        },
    )

    if findings:
        print("Claude Loop verification failed.", file=sys.stderr)
        print(f"Workspace: {workspace}", file=sys.stderr)
        for issue in findings:
            print(f"- {issue}", file=sys.stderr)
        print(f"Verification result: {result_path}", file=sys.stderr)
        return 1

    print("Claude Loop verification passed.")
    print(f"Workspace: {workspace}")
    print(f"Verification result: {result_path}")

    if args.cleanup:
        shutil.rmtree(workspace, ignore_errors=True)
        if created_tempdir:
            print("Temporary workspace removed after successful verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
