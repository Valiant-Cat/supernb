#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
PHASES = ["research", "prd", "design", "planning", "delivery", "release"]
SUPPORTED_HARNESSES = ["auto", "codex", "claude-code", "opencode"]
DIRECT_EXECUTION_HARNESSES = {"codex", "claude-code"}
REPORT_START = "SUPERNB_EXECUTION_REPORT_JSON_START"
REPORT_END = "SUPERNB_EXECUTION_REPORT_JSON_END"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute the current supernb next-command through a supported harness CLI.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", choices=PHASES, help="Phase to execute. Defaults to the selected phase from run-status.json.")
    parser.add_argument("--harness", choices=SUPPORTED_HARNESSES, default="auto", help="Harness to use. Defaults to auto-detect.")
    parser.add_argument("--project-dir", help="Working directory for the harness. Defaults to initiative delivery.project_dir, repository, or the supernb repo.")
    parser.add_argument("--prompt-file", help="Override the rendered prompt file. Defaults to the initiative next-command.md.")
    parser.add_argument("--cli-arg", action="append", default=[], help="Repeatable extra argument forwarded to the harness CLI.")
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke the harness. Only prepare the execution packet.")
    return parser.parse_args()


def try_load_pyyaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    return yaml.safe_load(text)


def parse_scalar(value: str) -> Any:
    if value in {'""', "''"}:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        inner = value[1:-1]
        return bytes(inner, "utf-8").decode("unicode_escape")
    lower = value.lower()
    if lower in {"true", "yes"}:
        return True
    if lower in {"false", "no"}:
        return False
    return value


def parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            raise ValueError(f"Unsupported YAML list syntax at line {lineno}: {raw_line}")
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise ValueError(f"Unsupported indentation at line {lineno}: {raw_line}")
        if ":" not in stripped:
            raise ValueError(f"Expected key/value pair at line {lineno}: {raw_line}")

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if value == "":
            child: dict[str, Any] = {}
            container[key] = child
            stack.append((indent, child))
        else:
            container[key] = parse_scalar(value)

    return root


def load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    loaded = try_load_pyyaml(text)
    if loaded is not None:
        return loaded
    return parse_simple_yaml(text)


def nested_get(data: dict[str, Any], *keys: str, default: str = "") -> str:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    if current is None:
        return default
    if isinstance(current, bool):
        return "yes" if current else "no"
    value = str(current).strip()
    if re.fullmatch(r"\{\{[^}]+\}\}", value):
        return default
    return value


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def artifact_path(spec: dict[str, Any], key: str, default: Path | None = None) -> Path:
    value = nested_get(spec, "artifacts", key)
    if value:
        return ROOT_DIR / value
    if default is not None:
        return default
    raise KeyError(f"Missing artifact path: {key}")


def resolve_spec_path(args: argparse.Namespace) -> Path:
    if args.spec:
        return Path(args.spec).expanduser().resolve()
    if args.initiative_id:
        return ROOT_DIR / "artifacts" / "initiatives" / args.initiative_id / "initiative.yaml"
    raise ValueError("Pass --initiative-id or --spec.")


def resolve_run_payload(spec: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    run_status_json = artifact_path(spec, "run_status_json")
    if not run_status_json.is_file():
        raise FileNotFoundError(f"Run status JSON not found: {run_status_json}. Run ./scripts/supernb run first.")
    return run_status_json, json.loads(run_status_json.read_text(encoding="utf-8"))


def resolve_phase(args: argparse.Namespace, payload: dict[str, Any]) -> str:
    selected = str(payload.get("selected_phase", "")).strip()
    if not selected:
        raise ValueError("selected_phase missing in run-status.json")
    phase = args.phase or selected
    if args.phase and args.phase != selected and not args.prompt_file:
        raise ValueError(f"--phase {args.phase} does not match the current selected phase {selected}. Re-run ./scripts/supernb run first or pass --prompt-file explicitly.")
    return phase


def resolve_prompt_path(args: argparse.Namespace, payload: dict[str, Any]) -> Path:
    if args.prompt_file:
        return Path(args.prompt_file).expanduser().resolve()
    next_command = payload.get("next_command") or {}
    next_path = str(next_command.get("path", "")).strip()
    if not next_path:
        raise ValueError("No next command is available for the current phase. The phase may still be blocked.")
    return (ROOT_DIR / next_path).resolve()


def local_path_from_value(value: str) -> Path | None:
    if not value or "://" in value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (ROOT_DIR / path).resolve()
    else:
        path = path.resolve()
    return path if path.exists() else None


def resolve_project_dir(args: argparse.Namespace, spec: dict[str, Any]) -> Path:
    if args.project_dir:
        return Path(args.project_dir).expanduser().resolve()

    for candidate in [
        nested_get(spec, "delivery", "project_dir"),
        nested_get(spec, "delivery", "repository"),
    ]:
        path = local_path_from_value(candidate)
        if path:
            return path

    return ROOT_DIR


def available_harnesses() -> list[str]:
    available: list[str] = []
    if shutil.which("codex"):
        available.append("codex")
    if shutil.which("claude"):
        available.append("claude-code")
    if shutil.which("opencode"):
        available.append("opencode")
    return available


def marker_harness(project_dir: Path) -> str:
    if (project_dir / ".claude").is_dir():
        return "claude-code"
    if (project_dir / ".opencode").is_dir():
        return "opencode"
    return ""


def resolve_harness(args: argparse.Namespace, spec: dict[str, Any], project_dir: Path) -> str:
    if args.harness != "auto":
        return args.harness

    available = available_harnesses()
    preferred = nested_get(spec, "delivery", "harness_preference")
    if preferred in SUPPORTED_HARNESSES and preferred != "auto":
        return preferred

    marker = marker_harness(project_dir)
    if marker:
        return marker

    if len(available) == 1:
        return available[0]

    if not available:
        raise ValueError("Could not auto-detect a supported harness. Install codex, claude, or opencode; or pass --harness explicitly.")

    raise ValueError(f"Could not auto-detect a harness because multiple supported CLIs are installed: {', '.join(available)}. Pass --harness explicitly or set delivery.harness_preference in initiative.yaml.")


def build_execution_command(harness: str, project_dir: Path, response_path: Path, cli_args: list[str]) -> list[str]:
    if harness == "codex":
        return [
            "codex",
            "-a",
            "never",
            "exec",
            "-s",
            "workspace-write",
            "-C",
            str(project_dir),
            "--skip-git-repo-check",
            "-o",
            str(response_path),
            *cli_args,
            "-",
        ]
    if harness == "claude-code":
        return [
            "claude",
            "-p",
            "--output-format",
            "text",
            "--permission-mode",
            "auto",
            *cli_args,
        ]
    raise ValueError(f"Direct execution is not supported for harness: {harness}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def default_gate_status(phase: str) -> str:
    return {
        "research": "approved",
        "prd": "approved",
        "design": "approved",
        "planning": "ready",
        "delivery": "verified",
        "release": "ready",
    }[phase]


def response_contract(phase: str) -> str:
    gate_status = default_gate_status(phase)
    return (
        "\n\nFinal response requirement for supernb:\n"
        "After your normal response, append a machine-readable JSON block between these exact markers:\n"
        f"{REPORT_START}\n"
        "{\n"
        '  "completion_status": "completed|partial|blocked|needs-input",\n'
        '  "summary": "short summary",\n'
        '  "completed_items": ["..."],\n'
        '  "remaining_items": ["..."],\n'
        '  "evidence_artifacts": ["path/or/file"],\n'
        '  "commands_run": ["command"],\n'
        '  "tests_run": ["test or verification command"],\n'
        '  "recommended_result_status": "succeeded|needs-follow-up|blocked|manual-follow-up",\n'
        '  "recommended_gate_action": "none|certify|advance",\n'
        f'  "recommended_gate_status": "{gate_status}|pending|",\n'
        '  "follow_up": ["..."]\n'
        "}\n"
        f"{REPORT_END}\n"
        "Rules:\n"
        "- Use valid JSON only between the markers.\n"
        "- Keep arrays as arrays of strings.\n"
        "- Only list evidence_artifacts that were actually created, updated, or are central proof of the work.\n"
        "- Prefer recommended_gate_action=certify unless the phase is truly ready to advance.\n"
    )


def ensure_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        items = [str(value).strip()] if str(value).strip() else []
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_report_json(text: str) -> dict[str, Any] | None:
    pattern = re.compile(rf"{REPORT_START}\s*(\{{.*?\}})\s*{REPORT_END}", re.DOTALL)
    match = pattern.search(text)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    completion_status = ensure_string(parsed.get("completion_status")).lower()
    if completion_status not in {"completed", "partial", "blocked", "needs-input"}:
        completion_status = "partial"

    recommended_result_status = ensure_string(parsed.get("recommended_result_status")).lower()
    if recommended_result_status not in {"succeeded", "needs-follow-up", "blocked", "manual-follow-up"}:
        recommended_result_status = ""

    recommended_gate_action = ensure_string(parsed.get("recommended_gate_action")).lower()
    if recommended_gate_action not in {"none", "certify", "advance"}:
        recommended_gate_action = "none"

    return {
        "completion_status": completion_status,
        "summary": ensure_string(parsed.get("summary")),
        "completed_items": ensure_list(parsed.get("completed_items")),
        "remaining_items": ensure_list(parsed.get("remaining_items")),
        "evidence_artifacts": ensure_list(parsed.get("evidence_artifacts")),
        "commands_run": ensure_list(parsed.get("commands_run")),
        "tests_run": ensure_list(parsed.get("tests_run")),
        "recommended_result_status": recommended_result_status,
        "recommended_gate_action": recommended_gate_action,
        "recommended_gate_status": ensure_string(parsed.get("recommended_gate_status")).lower(),
        "follow_up": ensure_list(parsed.get("follow_up")),
    }


def extract_bullet_section(text: str, headings: list[str]) -> list[str]:
    lines = text.splitlines()
    results: list[str] = []
    collecting = False
    heading_patterns = [re.compile(rf"^\s{{0,3}}#{{0,6}}\s*{pattern}\s*:?\s*$", re.IGNORECASE) for pattern in headings]

    for line in lines:
        stripped = line.strip()
        if any(pattern.match(stripped) for pattern in heading_patterns):
            collecting = True
            continue
        if collecting and re.match(r"^\s{0,3}#{1,6}\s+\S", stripped):
            break
        if collecting:
            bullet_match = re.match(r"^\s*[-*]\s+(.*)$", line)
            numbered_match = re.match(r"^\s*\d+\.\s+(.*)$", line)
            item = ""
            if bullet_match:
                item = bullet_match.group(1).strip()
            elif numbered_match:
                item = numbered_match.group(1).strip()
            elif stripped:
                if results:
                    results[-1] = f"{results[-1]} {stripped}".strip()
                continue
            if item:
                results.append(item)
    return results


def extract_candidate_paths(text: str) -> list[str]:
    candidates = re.findall(r"(?:[\w./-]+/)+[\w.-]+", text)
    valid: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip().strip("`")
        if candidate in seen:
            continue
        if candidate.startswith("./"):
            candidate = candidate[2:]
        if "/" not in candidate:
            continue
        seen.add(candidate)
        valid.append(candidate)
    return valid


def heuristic_report_from_text(phase: str, status: str, response_text: str, stderr_text: str, excerpt: str, stderr_excerpt: str) -> dict[str, Any]:
    completed_items = extract_bullet_section(response_text, [r"completed", r"done", r"implemented", r"finished"])
    remaining_items = extract_bullet_section(response_text, [r"remaining", r"open items?", r"next steps?", r"follow[- ]?up"])
    tests_run = extract_bullet_section(response_text, [r"tests?", r"verification", r"checks?"])
    commands_run = extract_bullet_section(response_text, [r"commands? run", r"commands?", r"shell commands?"])
    evidence_artifacts = extract_bullet_section(response_text, [r"files changed", r"artifacts?", r"evidence"])
    if not evidence_artifacts:
        evidence_artifacts = extract_candidate_paths(response_text)

    if status == "succeeded":
        completion_status = "completed" if not remaining_items else "partial"
        recommended_result_status = "succeeded" if completion_status == "completed" else "needs-follow-up"
        recommended_gate_action = "certify" if completion_status == "completed" else "none"
    elif status == "failed":
        completion_status = "blocked"
        recommended_result_status = "blocked"
        recommended_gate_action = "none"
    elif status == "unsupported":
        completion_status = "needs-input"
        recommended_result_status = "manual-follow-up"
        recommended_gate_action = "none"
    else:
        completion_status = "needs-input"
        recommended_result_status = "manual-follow-up"
        recommended_gate_action = "none"

    summary = excerpt or stderr_excerpt or f"{phase} execution ended with status {status}."
    follow_up = remaining_items[:]
    if not follow_up:
        if status == "failed":
            follow_up = ["Inspect stderr.log and fix the execution failure."]
        elif status == "unsupported":
            follow_up = ["Run the prepared prompt manually in the target harness."]
        elif status == "prepared":
            follow_up = ["Rerun execute-next without --dry-run."]

    return {
        "completion_status": completion_status,
        "summary": summary,
        "completed_items": completed_items,
        "remaining_items": remaining_items,
        "evidence_artifacts": evidence_artifacts,
        "commands_run": commands_run,
        "tests_run": tests_run,
        "recommended_result_status": recommended_result_status,
        "recommended_gate_action": recommended_gate_action,
        "recommended_gate_status": default_gate_status(phase) if recommended_gate_action in {"certify", "advance"} else "",
        "follow_up": follow_up,
    }


def short_text_excerpt(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("```"):
            continue
        if len(stripped) > 220:
            return stripped[:217] + "..."
        return stripped
    return ""


def build_result_suggestion(
    phase: str,
    harness: str,
    status: str,
    dry_run: bool,
    exit_code: int | None,
    response_text: str,
    stderr_text: str,
    packet_dir: Path,
) -> dict[str, Any]:
    excerpt = short_text_excerpt(response_text)
    stderr_excerpt = short_text_excerpt(stderr_text)
    structured_report = extract_report_json(response_text)
    report_source = "structured-report" if structured_report else "heuristic"

    if not structured_report:
        structured_report = heuristic_report_from_text(phase, status, response_text, stderr_text, excerpt, stderr_excerpt)

    if dry_run:
        result_status = "not-run"
        summary = f"{phase} execution packet prepared for {harness}; no harness run yet."
        next_step = "rerun execute-next without --dry-run"
    elif status == "unsupported":
        result_status = "manual-follow-up"
        summary = f"{phase} execution requires manual handoff because direct {harness} bridging is unavailable."
        next_step = "run the prepared prompt manually in the target harness"
    elif status == "failed":
        result_status = "blocked"
        summary = structured_report.get("summary") or stderr_excerpt or excerpt or f"{phase} execution failed in {harness} with exit code {exit_code}."
        next_step = "inspect stderr.log and fix the failure before rerunning"
    else:
        result_status = ensure_string(structured_report.get("recommended_result_status")).lower() or "succeeded"
        summary = structured_report.get("summary") or excerpt or f"{phase} execution completed successfully in {harness}."
        gate_action = ensure_string(structured_report.get("recommended_gate_action")).lower()
        if gate_action == "advance":
            next_step = f"apply the execution packet, then certify or advance toward {ensure_string(structured_report.get('recommended_gate_status')) or default_gate_status(phase)}"
        elif gate_action == "certify":
            next_step = "apply the execution packet, then certify the phase"
        else:
            next_step = "apply the execution packet and review follow-up items"

    return {
        "phase": phase,
        "harness": harness,
        "execution_status": status,
        "dry_run": dry_run,
        "exit_code": exit_code,
        "suggested_result_status": result_status,
        "suggested_summary": summary,
        "response_excerpt": excerpt,
        "stderr_excerpt": stderr_excerpt,
        "suggested_next_step": next_step,
        "packet_dir": display_path(packet_dir),
        "source": report_source,
        "execution_report": structured_report,
    }


def write_result_suggestion_md(
    path: Path,
    initiative_id: str,
    suggestion: dict[str, Any],
    packet_dir: Path,
) -> None:
    phase = suggestion["phase"]
    lines = [
        "# Result Suggestion",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Phase: `{phase}`",
        f"- Harness: `{suggestion['harness']}`",
        f"- Execution status: `{suggestion['execution_status']}`",
        f"- Dry run: `{'yes' if suggestion['dry_run'] else 'no'}`",
        f"- Suggestion source: `{suggestion['source']}`",
        f"- Suggested result status: `{suggestion['suggested_result_status']}`",
        f"- Suggested summary: {suggestion['suggested_summary']}",
        f"- Suggested next step: {suggestion['suggested_next_step']}",
        "",
        "## Suggested Commands",
        "",
        f"- Record result: `./scripts/supernb apply-execution --initiative-id {initiative_id} --packet {packet_dir}`",
        f"- Record result and certify: `./scripts/supernb apply-execution --initiative-id {initiative_id} --packet {packet_dir} --certify`",
        f"- Record result and certify+apply: `./scripts/supernb apply-execution --initiative-id {initiative_id} --packet {packet_dir} --apply-certification`",
        "",
        "## Evidence",
        "",
        f"- Packet summary: `{display_path(packet_dir / 'summary.md')}`",
        f"- Response: `{display_path(packet_dir / 'response.md')}`",
        f"- Stdout: `{display_path(packet_dir / 'stdout.log')}`",
        f"- Stderr: `{display_path(packet_dir / 'stderr.log')}`",
    ]
    report = suggestion.get("execution_report") or {}
    if report.get("completed_items"):
        lines.extend(["", "## Completed Items", ""])
        for item in report["completed_items"]:
            lines.append(f"- {item}")
    if report.get("remaining_items"):
        lines.extend(["", "## Remaining Items", ""])
        for item in report["remaining_items"]:
            lines.append(f"- {item}")
    if report.get("evidence_artifacts"):
        lines.extend(["", "## Evidence Artifacts", ""])
        for item in report["evidence_artifacts"]:
            lines.append(f"- `{item}`")
    if report.get("commands_run"):
        lines.extend(["", "## Commands Run", ""])
        for item in report["commands_run"]:
            lines.append(f"- `{item}`")
    if report.get("tests_run"):
        lines.extend(["", "## Tests Run", ""])
        for item in report["tests_run"]:
            lines.append(f"- `{item}`")
    if report.get("follow_up"):
        lines.extend(["", "## Follow Up", ""])
        for item in report["follow_up"]:
            lines.append(f"- {item}")
    if suggestion.get("response_excerpt"):
        lines.extend(["", "## Response Excerpt", "", suggestion["response_excerpt"]])
    if suggestion.get("stderr_excerpt"):
        lines.extend(["", "## Stderr Excerpt", "", suggestion["stderr_excerpt"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_run_log(
    log_path: Path,
    phase: str,
    harness: str,
    dry_run: bool,
    status: str,
    exit_code: int | None,
    packet_dir: Path,
    prompt_path: Path,
    response_path: Path,
    suggestion_path: Path,
) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")

    lines = [
        f"## {utc_now()} execution",
        "",
        f"- Phase: `{phase}`",
        f"- Harness: `{harness}`",
        f"- Dry run: `{'yes' if dry_run else 'no'}`",
        f"- Execution status: `{status}`",
        f"- Exit code: `{exit_code if exit_code is not None else 'not-run'}`",
        f"- Execution packet: `{display_path(packet_dir)}`",
        f"- Prompt: `{display_path(prompt_path)}`",
        f"- Response: `{display_path(response_path)}`",
        f"- Result suggestion: `{display_path(suggestion_path)}`",
        "",
    ]
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def write_summary(
    summary_path: Path,
    initiative_id: str,
    phase: str,
    harness: str,
    project_dir: Path,
    dry_run: bool,
    status: str,
    exit_code: int | None,
    packet_dir: Path,
    prompt_source: Path,
    prompt_with_report_path: Path,
    response_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    result_suggestion_path: Path,
    command_argv: list[str] | None,
) -> None:
    lines = [
        "# Execution Packet",
        "",
        f"- Initiative ID: `{initiative_id}`",
        f"- Phase: `{phase}`",
        f"- Harness: `{harness}`",
        f"- Recorded: `{utc_now()}`",
        f"- Dry run: `{'yes' if dry_run else 'no'}`",
        f"- Status: `{status}`",
        f"- Exit code: `{exit_code if exit_code is not None else 'not-run'}`",
        f"- Project dir: `{display_path(project_dir)}`",
        f"- Packet dir: `{display_path(packet_dir)}`",
        f"- Prompt source: `{display_path(prompt_source)}`",
        "",
        "## Files",
        "",
        f"- Prompt copy: `{display_path(packet_dir / 'prompt.md')}`",
        f"- Prompt with report contract: `{display_path(prompt_with_report_path)}`",
        f"- Request metadata: `{display_path(packet_dir / 'request.json')}`",
        f"- Response: `{display_path(response_path)}`",
        f"- Stdout: `{display_path(stdout_path)}`",
        f"- Stderr: `{display_path(stderr_path)}`",
        f"- Result suggestion: `{display_path(result_suggestion_path)}`",
        "",
        "## Command",
        "",
    ]
    if command_argv:
        lines.append(f"`{shlex.join(command_argv)}`")
    else:
        lines.append("- Not executed because only packet preparation was possible.")

    lines.extend(["", "## Next Action", ""])
    if dry_run:
        lines.append("- Review the execution packet, then rerun without `--dry-run` when you are ready.")
    elif status == "unsupported":
        lines.append("- Review `result-suggestion.md`, then use `./scripts/supernb apply-execution --initiative-id <id> --packet <packet-dir>` to record the manual-follow-up result.")
    elif status == "failed":
        lines.append("- Review `result-suggestion.md`, then use `./scripts/supernb apply-execution --initiative-id <id> --packet <packet-dir>` to record the blocked result before rerunning if needed.")
    else:
        lines.append("- Review `result-suggestion.md`, then apply it with `./scripts/supernb apply-execution --initiative-id <id> --packet <packet-dir>`.")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    try:
        _, payload = resolve_run_payload(spec)
        phase = resolve_phase(args, payload)
        prompt_source = resolve_prompt_path(args, payload)
        project_dir = resolve_project_dir(args, spec)
        harness = resolve_harness(args, spec, project_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not prompt_source.is_file():
        print(f"Prompt file not found: {prompt_source}", file=sys.stderr)
        return 1

    prompt_text = prompt_source.read_text(encoding="utf-8")
    executions_dir = artifact_path(
        spec,
        "executions_dir",
        ROOT_DIR / "artifacts" / "initiatives" / initiative_id / "executions",
    )
    run_log_path = artifact_path(spec, "run_log_md")
    packet_dir = executions_dir / f"{timestamp_slug()}-{phase}-{harness}"
    packet_dir.mkdir(parents=True, exist_ok=True)

    prompt_copy_path = packet_dir / "prompt.md"
    prompt_copy_path.write_text(prompt_text, encoding="utf-8")
    prompt_with_report_path = packet_dir / "prompt-with-report.md"
    prompt_with_report_text = prompt_text + response_contract(phase)
    prompt_with_report_path.write_text(prompt_with_report_text, encoding="utf-8")
    response_path = packet_dir / "response.md"
    stdout_path = packet_dir / "stdout.log"
    stderr_path = packet_dir / "stderr.log"
    summary_path = packet_dir / "summary.md"
    request_path = packet_dir / "request.json"
    result_suggestion_json = packet_dir / "result-suggestion.json"
    result_suggestion_md = packet_dir / "result-suggestion.md"

    status = "prepared"
    exit_code: int | None = None
    command_argv: list[str] | None = None
    error_message = ""

    if harness not in DIRECT_EXECUTION_HARNESSES:
        status = "unsupported"
        error_message = f"Direct execute-next support is not available for harness: {harness}"
    else:
        binary = "codex" if harness == "codex" else "claude"
        if not shutil.which(binary):
            status = "unsupported"
            error_message = f"{binary} CLI is not installed or not on PATH."
        else:
            command_argv = build_execution_command(harness, project_dir, response_path, args.cli_arg)

    write_json(
        request_path,
        {
            "initiative_id": initiative_id,
            "phase": phase,
            "harness": harness,
            "generated_at": utc_now(),
            "prompt_source": display_path(prompt_source),
            "prompt_copy": display_path(prompt_copy_path),
            "prompt_with_report": display_path(prompt_with_report_path),
            "project_dir": str(project_dir),
            "dry_run": args.dry_run,
            "command": command_argv or [],
            "cli_args": args.cli_arg,
        },
    )

    if args.dry_run:
        status = "prepared"
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        response_path.write_text(
            "# Dry Run\n\n- No harness was invoked.\n- Review `request.json` and rerun without `--dry-run`.\n",
            encoding="utf-8",
        )
    elif status == "unsupported":
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(error_message + "\n", encoding="utf-8")
        response_path.write_text(
            "# Direct Execution Unavailable\n\n"
            f"- {error_message}\n"
            "- Use the prepared prompt manually in the target harness.\n",
            encoding="utf-8",
        )
    else:
        proc = subprocess.run(
            command_argv,
            input=prompt_with_report_text,
            text=True,
            capture_output=True,
            cwd=str(project_dir),
        )
        exit_code = proc.returncode
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")

        if harness == "claude-code":
            response_path.write_text(proc.stdout, encoding="utf-8")
        elif not response_path.exists():
            response_path.write_text("", encoding="utf-8")

        status = "succeeded" if proc.returncode == 0 else "failed"

    response_text = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
    suggestion = build_result_suggestion(phase, harness, status, args.dry_run, exit_code, response_text, stderr_text, packet_dir)
    write_json(result_suggestion_json, suggestion)
    write_result_suggestion_md(result_suggestion_md, initiative_id, suggestion, packet_dir)

    write_summary(
        summary_path,
        initiative_id,
        phase,
        harness,
        project_dir,
        args.dry_run,
        status,
        exit_code,
        packet_dir,
        prompt_source,
        prompt_with_report_path,
        response_path,
        stdout_path,
        stderr_path,
        result_suggestion_md,
        command_argv,
    )
    append_run_log(run_log_path, phase, harness, args.dry_run, status, exit_code, packet_dir, prompt_source, response_path, result_suggestion_md)

    print(f"Initiative: {initiative_id}")
    print(f"Phase: {phase}")
    print(f"Harness: {harness}")
    print(f"Project dir: {project_dir}")
    print(f"Execution packet: {packet_dir}")
    print(f"Summary: {summary_path}")
    print(f"Response: {response_path}")
    print(f"Result suggestion: {result_suggestion_md}")
    if command_argv:
        print(f"Command: {shlex.join(command_argv)}")
    else:
        print("Command: not available for direct execution")
    print(f"Status: {status}")

    if status == "failed":
        return exit_code or 1
    if status == "unsupported" and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
