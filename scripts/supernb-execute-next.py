#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.supernb_common import (
    PHASES,
    append_debug_log as common_append_debug_log,
    artifact_path as common_artifact_path,
    display_path as common_display_path,
    load_spec,
    nested_get,
    phase_targets as common_phase_targets,
    project_root as common_project_root,
    resolve_spec_path as common_resolve_spec_path,
    supernb_cli_prefix,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]
RALPH_LOOP_SETUP_SCRIPT = ROOT_DIR / "upstreams" / "dotclaude" / "superpowers" / "scripts" / "setup-superpower-loop.sh"
RALPH_LOOP_AUDIT_WATCHER = ROOT_DIR / "scripts" / "supernb-loop-audit-watcher.py"
RALPH_LOOP_PLUGIN_DIR = ROOT_DIR / "upstreams" / "dotclaude" / "superpowers" / ".claude-plugin"
SUPPORTED_HARNESSES = ["auto", "codex", "claude-code", "opencode"]
DIRECT_EXECUTION_HARNESSES = {"codex", "claude-code"}
REPORT_START = "SUPERNB_EXECUTION_REPORT_JSON_START"
REPORT_END = "SUPERNB_EXECUTION_REPORT_JSON_END"
LOOP_REQUIRED_PHASES = {"planning", "delivery"}
CLAUDE_LOOP_HARNESSES = {"claude-code", "claude-code-prompt"}
LOOP_MAX_ITERATIONS = {"planning": 6, "delivery": 8}
METADATA_FIELDS = {
    "Initiative ID",
    "Product",
    "Research date",
    "Prepared",
    "Status",
    "Approval status",
    "Ready for execution",
    "Delivery status",
    "Release decision",
    "Approved by",
    "Approved on",
}
SECTION_EXPECTATIONS = {
    "research": {
        "01-competitor-landscape.md": [
            "Research Window",
            "Competitor Shortlist",
            "Feature Surface Comparison",
            "Metadata Snapshot",
            "Monetization And Packaging",
            "Regional And Segment Signals",
            "Scale Signals And Market Headroom",
            "Observed Strategic Patterns",
            "Gaps To Investigate",
            "Raw Data References",
        ],
        "02-review-insights.md": [
            "Query Context",
            "Top Complaint Clusters",
            "Top Delight Clusters",
            "Jobs Users Are Hiring The Product To Do",
            "Explicit Feature Requests",
            "Anti-Features",
            "Version Or Country Hotspots",
            "Persona Or Segment Breakdowns",
            "Raw Data References",
        ],
        "03-feature-opportunities.md": [
            "Must-Have Features",
            "Prioritized Capability Map",
            "Differentiators",
            "Avoidances",
            "Open Hypotheses",
            "Scope Recommendation",
            "Recommendation",
            "Growth And Scale Recommendation",
        ],
    },
    "prd": {
        "product-requirements.md": [
            "Product Summary",
            "Problem Statement",
            "Target Users",
            "Market And Research Synthesis",
            "Product Goals",
            "Non-Goals",
            "Core User Journeys",
            "Feature System",
            "Functional Requirements",
            "Experience Principles",
            "Localization Requirements",
            "Business Model",
            "Growth System",
            "Success Metrics",
            "Launch Scope And Sequencing",
            "Risks",
            "Operational And Trust Requirements",
            "Scale Readiness Requirements",
            "Cross-Phase Traceability Matrix",
            "Evidence Appendix",
        ],
    },
    "design": {
        "ui-ux-spec.md": [
            "Design Context",
            "Product Experience Strategy",
            "Visual Direction",
            "Accessibility And Readability Rules",
            "Localization And Copy Rules",
            "Information Architecture",
            "User Flow Coverage",
            "Page Specs",
            "State Matrix",
            "Key Journey Surface Deep Dives",
            "Design System Definition",
            "Component Rules",
            "Responsive And Platform Behavior",
            "Interaction And Motion Details",
            "Trust And Feedback Cues",
            "Scale UX Requirements",
            "Conversion And Retention Surfaces",
            "Traceability To Research And PRD",
            "Impeccable Review Notes",
        ],
        "i18n-strategy.md": [
            "Localization Scope",
            "Locale Prioritization",
            "Stack And Resource Model",
            "Source Of Truth",
            "Copy Governance",
            "Delivery Rules",
            "Layout And UX Considerations",
            "Validation",
        ],
    },
    "planning": {
        "implementation-plan.md": [
            "Scope For This Plan",
            "Architecture And Technical Strategy",
            "Milestones",
            "Dependency And Risk Map",
            "Task Batches",
            "Localization Work",
            "Review And Verification Cadence",
            "Loop Candidates",
            "Verification Commands",
            "Commit Strategy",
            "Rollout And Recovery Plan",
            "Scale And Reliability Workstreams",
            "Delivery Traceability Map",
        ],
    },
    "delivery": {
        "implementation-plan.md": [
            "Scope For This Plan",
            "Architecture And Technical Strategy",
            "Milestones",
            "Dependency And Risk Map",
            "Task Batches",
            "Localization Work",
            "Review And Verification Cadence",
            "Verification Commands",
            "Commit Strategy",
            "Rollout And Recovery Plan",
            "Scale And Reliability Workstreams",
            "Delivery Traceability Map",
        ],
        "release-readiness.md": [
            "Verification Summary",
            "UX Audit Summary",
            "Localization Summary",
            "Operational Readiness",
            "Rollout And Rollback Plan",
            "Scale Launch Controls",
            "Post-Launch Watchlist",
            "Delivered Traceability Summary",
        ],
    },
    "release": {
        "release-readiness.md": [
            "Verification Summary",
            "UX Audit Summary",
            "Localization Summary",
            "Operational Readiness",
            "Release Checklist",
            "Known Issues",
            "Rollout And Rollback Plan",
            "Scale Launch Controls",
            "Post-Launch Watchlist",
            "Delivered Traceability Summary",
            "Release Notes Draft",
            "Go Or No-Go Rationale",
        ],
    },
}
WORKFLOW_TRACE_KEYS = [
    "brainstorming",
    "writing_plans",
    "test_driven_development",
    "code_review",
    "using_git_worktrees",
    "subagent_or_executing_plans",
]
TRACEABILITY_ARTIFACTS = {
    "prd": {
        "artifact_key": "prd_dir",
        "filename": "product-requirements.md",
        "section": "Cross-Phase Traceability Matrix",
        "trace_id_headers": ["Trace ID"],
        "capability_headers": ["PRD capability"],
        "surface_headers": ["Primary design surface"],
        "reference_headers": ["Research insight or review theme"],
    },
    "design": {
        "artifact_key": "design_dir",
        "filename": "ui-ux-spec.md",
        "section": "Traceability To Research And PRD",
        "trace_id_headers": ["Trace ID"],
        "capability_headers": ["PRD capability"],
        "surface_headers": ["Primary design surface"],
        "reference_headers": ["Research insight reference"],
    },
    "plan": {
        "artifact_key": "plan_dir",
        "filename": "implementation-plan.md",
        "section": "Delivery Traceability Map",
        "trace_id_headers": ["Trace ID"],
        "capability_headers": ["PRD capability"],
        "surface_headers": ["Design surface"],
        "reference_headers": [],
    },
    "release": {
        "artifact_key": "release_dir",
        "filename": "release-readiness.md",
        "section": "Delivered Traceability Summary",
        "trace_id_headers": ["Trace ID"],
        "capability_headers": ["PRD capability"],
        "surface_headers": ["Design surface"],
        "reference_headers": [],
    },
}
TRACEABILITY_COMPARISONS = {
    "design": [("prd", "design", True)],
    "planning": [("prd", "design", True), ("design", "plan", False)],
    "delivery": [("prd", "design", True), ("design", "plan", False), ("plan", "release", False)],
    "release": [("prd", "design", True), ("design", "plan", False), ("plan", "release", False)],
}


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


def display_path(path: Path) -> str:
    return common_display_path(path, DISPLAY_ROOTS)


def project_root(spec: dict[str, Any]) -> Path:
    return common_project_root(spec, ROOT_DIR)


def artifact_path(spec: dict[str, Any], key: str, default: Path | None = None) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR, default=default)


def phase_targets(spec: dict[str, Any], phase: str) -> list[Path]:
    return common_phase_targets(spec, phase, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def debug_log(spec: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    common_append_debug_log(spec, ROOT_DIR, "supernb-execute-next", event, payload)


def resolve_run_payload(spec: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    run_status_json = artifact_path(spec, "run_status_json")
    if not run_status_json.is_file():
        raise FileNotFoundError(f"Run status JSON not found: {run_status_json}. Run {supernb_cli_prefix(ROOT_DIR)} run first.")
    return run_status_json, json.loads(run_status_json.read_text(encoding="utf-8"))


def resolve_phase(args: argparse.Namespace, payload: dict[str, Any]) -> str:
    selected = str(payload.get("selected_phase", "")).strip()
    if not selected:
        raise ValueError("selected_phase missing in run-status.json")
    phase = args.phase or selected
    if args.phase and args.phase != selected and not args.prompt_file:
        raise ValueError(
            f"--phase {args.phase} does not match the current selected phase {selected}. "
            f"Re-run {supernb_cli_prefix(ROOT_DIR)} run first or pass --prompt-file explicitly."
        )
    return phase


def resolve_prompt_path(args: argparse.Namespace, payload: dict[str, Any], spec: dict[str, Any]) -> Path:
    if args.prompt_file:
        return Path(args.prompt_file).expanduser().resolve()
    try:
        return artifact_path(spec, "next_command_md")
    except KeyError:
        next_command = payload.get("next_command") or {}
        next_path = str(next_command.get("path", "")).strip()
        if not next_path:
            raise ValueError("No next command is available for the current phase. The phase may still be blocked.")
        candidate = Path(next_path).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (project_root(spec) / candidate).resolve()


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


def build_execution_command(
    harness: str,
    project_dir: Path,
    response_path: Path,
    cli_args: list[str],
    loop_contract: dict[str, Any] | None = None,
) -> list[str]:
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
        command = [
            "claude",
            "-p",
            "--output-format",
            "text",
            "--permission-mode",
            "auto",
        ]
        if loop_contract:
            command.extend(
                [
                    "--plugin-dir",
                    str(loop_contract["plugin_dir"]),
                    "--session-id",
                    loop_contract["session_id"],
                ]
            )
        command.extend(cli_args)
        return command
    raise ValueError(f"Direct execution is not supported for harness: {harness}")


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized or "initiative"


def build_direct_loop_contract(initiative_id: str, phase: str, packet_dir: Path, project_dir: Path) -> dict[str, Any]:
    slug = slugify(f"{initiative_id}-{phase}-{packet_dir.name}")
    completion_promise = f"SUPERNB {initiative_id} {phase} batch complete"
    session_id = str(uuid.uuid4())
    state_file = project_dir / ".claude" / f"superpower-loop-{slug}.local.md"
    prompt_file = packet_dir / "ralph-loop-prompt.md"
    audit_summary_file = packet_dir / "ralph-loop-audit.json"
    audit_events_file = packet_dir / "ralph-loop-audit.ndjson"
    start_command = [
        "bash",
        str(RALPH_LOOP_SETUP_SCRIPT),
        "--prompt-file",
        str(prompt_file),
        "--completion-promise",
        completion_promise,
        "--max-iterations",
        str(LOOP_MAX_ITERATIONS.get(phase, 4)),
        "--state-file",
        str(state_file),
    ]
    return {
        "completion_promise": completion_promise,
        "session_id": session_id,
        "state_file": state_file,
        "prompt_file": prompt_file,
        "audit_summary_file": audit_summary_file,
        "audit_events_file": audit_events_file,
        "plugin_dir": RALPH_LOOP_PLUGIN_DIR,
        "max_iterations": LOOP_MAX_ITERATIONS.get(phase, 4),
        "start_command": start_command,
        "start_command_text": shlex.join(start_command),
    }


def direct_loop_policy(loop_contract: dict[str, Any]) -> str:
    return (
        "\n\nClaude Code Ralph Loop contract:\n"
        f"- Session id: `{loop_contract['session_id']}`.\n"
        f"- Session-local plugin dir: `{loop_contract['plugin_dir']}`.\n"
        f"- Ralph Loop has been armed for this run with state file `{loop_contract['state_file']}`.\n"
        f"- External audit summary: `{loop_contract['audit_summary_file']}`.\n"
        f"- External audit events: `{loop_contract['audit_events_file']}`.\n"
        f"- Add `{loop_contract['audit_summary_file']}` to evidence_artifacts.\n"
        f"- loop_execution.evidence must equal `{loop_contract['audit_summary_file']}`.\n"
        f"- When the run is genuinely complete, the final response must include `<promise>{loop_contract['completion_promise']}</promise>` as the last line.\n"
    )


def start_loop_audit_watcher(loop_contract: dict[str, Any], project_dir: Path, expected_session_id: str = "") -> None:
    subprocess.Popen(
        [
            sys.executable,
            str(RALPH_LOOP_AUDIT_WATCHER),
            "--state-file",
            str(loop_contract["state_file"]),
            "--summary-json",
            str(loop_contract["audit_summary_file"]),
            "--events-ndjson",
            str(loop_contract["audit_events_file"]),
            "--completion-promise",
            loop_contract["completion_promise"],
            "--max-iterations",
            str(loop_contract["max_iterations"]),
            "--expected-session-id",
            expected_session_id,
        ],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def local_ralph_loop_plugin_metadata() -> dict[str, str]:
    plugin_json = RALPH_LOOP_PLUGIN_DIR / "plugin.json"
    if not plugin_json.is_file():
        raise FileNotFoundError(f"Ralph Loop Claude plugin manifest not found: {plugin_json}")
    try:
        payload = json.loads(plugin_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ralph Loop Claude plugin manifest is invalid JSON: {plugin_json}") from exc
    name = str(payload.get("name", "")).strip() or "superpowers"
    version = str(payload.get("version", "")).strip()
    return {
        "id": "superpowers@frad-dotclaude",
        "name": name,
        "version": version,
        "source": str(RALPH_LOOP_PLUGIN_DIR),
        "mode": "session-local-plugin-dir",
    }


def finalize_loop_audit_summary(loop_contract: dict[str, Any], payload: dict[str, Any], event: str) -> dict[str, Any]:
    summary_path = Path(loop_contract["audit_summary_file"]).resolve()
    events_path = Path(loop_contract["audit_events_file"]).resolve()
    payload = dict(payload)
    payload.update(
        {
            "removed_after_observation": True,
            "last_observed_at": utc_now(),
            "final_status": "state_removed",
            "watcher_finished_at": utc_now(),
        }
    )
    write_json(summary_path, payload)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "timestamp": utc_now(),
                    "event": event,
                    "last_iteration": int(payload.get("last_iteration", 0) or 0),
                    "session_id": str(payload.get("last_session_id", "")),
                },
                ensure_ascii=True,
            )
            + "\n"
        )
    return payload


def read_loop_audit_summary(summary_path: Path) -> dict[str, Any] | None:
    if not summary_path.is_file():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def start_direct_claude_loop(project_dir: Path, loop_contract: dict[str, Any]) -> dict[str, str]:
    if not RALPH_LOOP_SETUP_SCRIPT.is_file():
        raise FileNotFoundError(f"Ralph Loop setup script not found: {RALPH_LOOP_SETUP_SCRIPT}")
    if not RALPH_LOOP_AUDIT_WATCHER.is_file():
        raise FileNotFoundError(f"Ralph Loop audit watcher not found: {RALPH_LOOP_AUDIT_WATCHER}")
    if not RALPH_LOOP_PLUGIN_DIR.is_dir():
        raise FileNotFoundError(f"Ralph Loop Claude plugin directory not found: {RALPH_LOOP_PLUGIN_DIR}")
    stop_hook = RALPH_LOOP_PLUGIN_DIR.parent / "hooks" / "stop-hook.sh"
    if not stop_hook.is_file():
        raise FileNotFoundError(f"Ralph Loop stop hook not found: {stop_hook}")

    plugin_metadata = local_ralph_loop_plugin_metadata()
    loop_env = dict(os.environ)
    loop_env["CLAUDE_CODE_SESSION_ID"] = loop_contract["session_id"]
    proc = subprocess.run(
        loop_contract["start_command"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        env=loop_env,
    )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "unknown Ralph Loop setup error"
        raise RuntimeError(f"Failed to arm Ralph Loop for direct Claude execution: {message}")

    state_file = Path(loop_contract["state_file"]).resolve()
    if not state_file.is_file():
        raise RuntimeError(f"Ralph Loop setup completed without creating the state file: {state_file}")

    start_loop_audit_watcher(loop_contract, project_dir, loop_contract["session_id"])
    return plugin_metadata


def wait_for_loop_state_observed(loop_contract: dict[str, Any], timeout_seconds: float = 4.0) -> dict[str, Any] | None:
    summary_path = Path(loop_contract["audit_summary_file"]).resolve()
    deadline = time.time() + max(timeout_seconds, 0.5)
    while time.time() < deadline:
        payload = read_loop_audit_summary(summary_path)
        if payload and payload.get("state_observed"):
            return payload
        time.sleep(0.1)
    payload = read_loop_audit_summary(summary_path)
    if payload and payload.get("state_observed"):
        return payload
    return payload


def wait_for_loop_audit_summary(loop_contract: dict[str, Any], timeout_seconds: float = 12.0) -> dict[str, Any] | None:
    summary_path = Path(loop_contract["audit_summary_file"]).resolve()
    state_path = Path(loop_contract["state_file"]).resolve()
    deadline = time.time() + max(timeout_seconds, 0.5)
    while time.time() < deadline:
        payload = read_loop_audit_summary(summary_path)
        if payload and str(payload.get("final_status", "")).strip() not in {"", "watching"}:
            return payload
        if payload and not state_path.exists() and payload.get("state_observed"):
            return finalize_loop_audit_summary(loop_contract, payload, "state-removed-confirmed")
        time.sleep(0.2)
    payload = read_loop_audit_summary(summary_path)
    if payload:
        if str(payload.get("final_status", "")).strip() in {"", "watching"} and not state_path.exists() and payload.get("state_observed"):
            return finalize_loop_audit_summary(loop_contract, payload, "state-removed-timeout-confirmed")
        return payload
    return None


def extract_promise_text(text: str) -> str:
    match = re.search(r"<promise>(.*?)</promise>", text, re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).strip().split())


def resolve_loop_audit_summary(project_dir: Path, packet_dir: Path, report: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    loop_execution = report.get("loop_execution") or {}
    evidence_path = ensure_string(loop_execution.get("evidence"))
    if not evidence_path:
        return None, ""
    candidates = [Path(evidence_path).expanduser()]
    if not candidates[0].is_absolute():
        candidates.extend([(project_dir / evidence_path).resolve(), (packet_dir / evidence_path).resolve()])
    for candidate in candidates:
        if candidate.is_file():
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None, str(candidate)
            if isinstance(payload, dict):
                return payload, str(candidate)
            return None, str(candidate)
    return None, evidence_path


def serialize_loop_contract(loop_contract: dict[str, Any] | None) -> dict[str, Any] | None:
    if not loop_contract:
        return None
    return {
        "completion_promise": loop_contract["completion_promise"],
        "session_id": loop_contract["session_id"],
        "state_file": str(loop_contract["state_file"]),
        "prompt_file": str(loop_contract["prompt_file"]),
        "audit_summary_file": str(loop_contract["audit_summary_file"]),
        "audit_events_file": str(loop_contract["audit_events_file"]),
        "plugin_dir": str(loop_contract["plugin_dir"]),
        "max_iterations": loop_contract["max_iterations"],
        "start_command": list(loop_contract["start_command"]),
        "start_command_text": loop_contract["start_command_text"],
    }


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


def execution_policy(spec: dict[str, Any], phase: str, project_dir: Path) -> str:
    initiative_id = nested_get(spec, "initiative", "id")
    artifact_lines = [f"- `{display_path(path)}`" for path in phase_targets(spec, phase)]
    lines = [
        "",
        "",
        "supernb execution policy:",
        f"- Initiative ID: `{initiative_id}`",
        f"- Product workspace: `{display_path(project_dir)}`",
        f"- Current phase: `{phase}`",
        "- Use upstream superpowers aggressively. Release the full workflow instead of collapsing everything into one opaque coding pass.",
        "- Break work into the smallest safe tasks you can justify. Favor 2-5 minute batches with explicit file paths, checks, and completion criteria.",
        "- Research, PRD, design, and planning artifacts must exist and be updated before claiming implementation completion.",
        "- Save changes into the initiative artifacts for this phase before reporting success.",
        "- Record whether brainstorming, writing-plans, TDD, code review, worktrees, and subagent/executing-plans were used in this run.",
        "- If a required workflow was intentionally skipped, say so explicitly and explain why.",
        "",
        "Phase artifact targets:",
        *artifact_lines,
    ]

    if phase == "planning":
        lines.extend(
            [
                "",
                "Planning-specific requirements:",
                "- Write or refine the implementation plan before delivery work.",
                "- Produce very fine-grained task batches with exact file paths, RED-GREEN-REFACTOR steps, verification commands, and commit strategy.",
            ]
        )
    if phase == "delivery":
        lines.extend(
            [
                "",
                "Delivery-specific requirements:",
                "- Treat this run as exactly one validated delivery batch. Do not silently continue through the whole project in one shot.",
                "- Use test-driven development: write or update a failing test first, make it pass, then refactor.",
                "- Run code review on the batch before completion.",
                "- Create a git commit for this validated batch before you report success.",
                "- If you cannot create a commit, report the run as blocked or needs-follow-up instead of pretending the batch is complete.",
            ]
        )
    return "\n".join(lines)


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
        '  "artifacts_updated": ["path/or/file"],\n'
        '  "commands_run": ["command"],\n'
        '  "tests_run": ["test or verification command"],\n'
        '  "validated_batches_completed": 0,\n'
        '  "batch_commits": ["<sha> message"],\n'
        '  "workflow_trace": {\n'
        '    "brainstorming": {"used": true, "evidence": "..."},\n'
        '    "writing_plans": {"used": true, "evidence": "..."},\n'
        '    "test_driven_development": {"used": true, "evidence": "..."},\n'
        '    "code_review": {"used": true, "evidence": "..."},\n'
        '    "using_git_worktrees": {"used": false, "evidence": "not needed this run"},\n'
        '    "subagent_or_executing_plans": {"used": true, "evidence": "..."}\n'
        "  },\n"
        '  "loop_execution": {"used": false, "mode": "ralph-loop|none", "completion_promise": "", "state_file": "", "max_iterations": 0, "final_iteration": 0, "exit_reason": "", "evidence": ""},\n'
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
        "- workflow_trace must include every listed workflow key, even when a workflow was intentionally skipped.\n"
        "- For delivery, validated_batches_completed must reflect the number of verified batches completed in this run, and batch_commits must list the commit(s) created for those batches.\n"
        "- For Claude Code planning or delivery runs, loop_execution.used must be true and must record the real Ralph Loop state file, completion promise, iteration count, exit reason, and evidence.\n"
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


def ensure_bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes"}:
            return True
        if lowered in {"false", "no"}:
            return False
    return None


def normalize_workflow_trace(value: Any) -> dict[str, dict[str, Any]]:
    raw = value if isinstance(value, dict) else {}
    result: dict[str, dict[str, Any]] = {}
    for key in WORKFLOW_TRACE_KEYS:
        item = raw.get(key)
        if not isinstance(item, dict):
            item = {}
        result[key] = {
            "used": ensure_bool_or_none(item.get("used")),
            "evidence": ensure_string(item.get("evidence")),
        }
    return result


def normalize_loop_execution(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return {
        "used": ensure_bool_or_none(raw.get("used")),
        "mode": ensure_string(raw.get("mode")).lower(),
        "completion_promise": ensure_string(raw.get("completion_promise")),
        "state_file": ensure_string(raw.get("state_file")),
        "max_iterations": max(int(raw.get("max_iterations", 0) or 0), 0),
        "final_iteration": max(int(raw.get("final_iteration", 0) or 0), 0),
        "exit_reason": ensure_string(raw.get("exit_reason")),
        "evidence": ensure_string(raw.get("evidence")),
    }


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
        "artifacts_updated": ensure_list(parsed.get("artifacts_updated")),
        "commands_run": ensure_list(parsed.get("commands_run")),
        "tests_run": ensure_list(parsed.get("tests_run")),
        "validated_batches_completed": max(int(parsed.get("validated_batches_completed", 0) or 0), 0),
        "batch_commits": ensure_list(parsed.get("batch_commits")),
        "workflow_trace": normalize_workflow_trace(parsed.get("workflow_trace")),
        "loop_execution": normalize_loop_execution(parsed.get("loop_execution")),
        "recommended_result_status": recommended_result_status,
        "recommended_gate_action": recommended_gate_action,
        "recommended_gate_status": ensure_string(parsed.get("recommended_gate_status")).lower(),
        "follow_up": ensure_list(parsed.get("follow_up")),
    }


def missing_structured_report_issue(harness: str) -> str:
    return (
        "Harness response is missing the required REPORT JSON block between "
        f"{REPORT_START} and {REPORT_END}. Structured execution reports are mandatory "
        f"for certifiable packets from direct {harness} runs."
    )


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


def line_is_placeholder_bullet(stripped: str) -> bool:
    match = re.match(r"^- ([^:]+):\s*$", stripped)
    if not match:
        return False
    label = match.group(1).strip()
    return label not in METADATA_FIELDS


def line_is_placeholder_numbered(stripped: str) -> bool:
    return bool(re.match(r"^\d+\.\s+[^:]+:\s*$", stripped))


def line_is_empty_table_row(stripped: str) -> bool:
    if not stripped.startswith("|"):
        return False
    if re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", stripped):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return all(cell == "" for cell in cells)


def line_has_template_marker(stripped: str) -> bool:
    patterns = [
        r"\bPattern \d+:\s*$",
        r"\bGap \d+:\s*$",
        r"\bJourney \d+:\s*$",
        r"\bGoal \d+:\s*$",
        r"\bNon-goal \d+:\s*$",
        r"\bPage \d+\s*$",
        r"\bHotspot \d+:\s*$",
        r"\bBatch \d+\s*$",
    ]
    return any(re.search(pattern, stripped) for pattern in patterns)


def line_is_unchecked_release_checkbox(stripped: str, phase: str) -> bool:
    return phase == "release" and stripped.startswith("- [ ] ")


def is_placeholder_line(stripped: str, phase: str) -> bool:
    if "{{" in stripped and "}}" in stripped:
        return True
    if line_is_placeholder_bullet(stripped):
        return True
    if line_is_placeholder_numbered(stripped):
        return True
    if line_is_empty_table_row(stripped):
        return True
    if line_has_template_marker(stripped) and stripped.endswith(":"):
        return True
    if line_is_unchecked_release_checkbox(stripped, phase):
        return True
    return False


def useful_content_count(lines: list[str], phase: str) -> int:
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            continue
        if stripped in {"```", "```bash"}:
            continue
        if stripped.startswith("|") and re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", stripped):
            continue
        if is_placeholder_line(stripped, phase):
            continue
        count += 1
    return count


def bullet_field_map(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*-\s+([^:]+):\s*(.*)$", line.strip())
        if match:
            values[match.group(1).strip()] = match.group(2).strip().strip("`")
    return values


def numbered_item_values(lines: list[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        match = re.match(r"^\s*\d+\.\s+(.*)$", line.strip())
        if not match:
            continue
        value = match.group(1).strip().strip("`")
        if value and not line_is_placeholder_numbered(line.strip()):
            values.append(value)
    return values


def table_data_rows(lines: list[str], phase: str) -> list[list[str]]:
    rows: list[list[str]] = []
    in_table = False
    header_skipped = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            header_skipped = False
            continue
        if not in_table:
            in_table = True
            header_skipped = False
        if re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", stripped):
            continue
        if line_is_empty_table_row(stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(not cell for cell in cells):
            continue
        if any("{{" in cell and "}}" in cell for cell in cells):
            continue
        if not header_skipped:
            header_skipped = True
            continue
        rows.append(cells)
    return rows


def normalize_traceability_label(value: str) -> str:
    normalized = str(value or "").strip().strip("`").lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_table_header(value: str) -> str:
    normalized = str(value or "").strip().strip("`").lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def first_markdown_table(lines: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    raw_table: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table and raw_table:
                break
            continue
        in_table = True
        raw_table.append(stripped)

    if len(raw_table) < 2:
        return [], []

    headers = [cell.strip() for cell in raw_table[0].strip("|").split("|")]
    normalized_headers = [normalize_table_header(header) for header in headers]
    rows: list[dict[str, str]] = []
    for raw_line in raw_table[1:]:
        if re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", raw_line):
            continue
        if line_is_empty_table_row(raw_line):
            continue
        cells = [cell.strip() for cell in raw_line.strip("|").split("|")]
        if all(not cell for cell in cells):
            continue
        if any("{{" in cell and "}}" in cell for cell in cells):
            continue
        row: dict[str, str] = {}
        for index, header in enumerate(normalized_headers):
            row[header] = cells[index].strip() if index < len(cells) else ""
        rows.append(row)
    return headers, rows


def table_value_from_headers(row: dict[str, str], headers: list[str]) -> str:
    for header in headers:
        value = row.get(normalize_table_header(header), "").strip().strip("`")
        if value:
            return value
    return ""


def summarize_labels(labels: list[str], limit: int = 5) -> str:
    if len(labels) <= limit:
        return ", ".join(labels)
    remaining = len(labels) - limit
    preview = ", ".join(labels[:limit])
    return f"{preview}, +{remaining} more"


def code_block_commands(lines: list[str]) -> list[str]:
    commands: list[str] = []
    in_block = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        if not stripped or stripped.startswith("#"):
            continue
        commands.append(stripped)
    return commands


def checkbox_counts(lines: list[str]) -> tuple[int, int]:
    checked = 0
    total = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [x] "):
            checked += 1
            total += 1
        elif stripped.startswith("- [ ] "):
            total += 1
    return checked, total


def count_filled_fields(values: dict[str, str], labels: list[str]) -> int:
    count = 0
    for label in labels:
        value = values.get(label, "").strip()
        if value and not re.fullmatch(r"\{\{[^}]+\}\}", value):
            count += 1
    return count


def complete_page_blocks(lines: list[str]) -> int:
    return complete_named_blocks(
        lines,
        ["Purpose", "Core modules", "Primary CTA", "Empty/loading/error/success states"],
    )


def complete_named_blocks(lines: list[str], required_fields: list[str]) -> int:
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in lines:
        if raw_line.strip().startswith("### "):
            if current:
                blocks.append(current)
            current = [raw_line]
            continue
        if current:
            current.append(raw_line)
    if current:
        blocks.append(current)

    completed = 0
    for block in blocks:
        values = bullet_field_map(block)
        if count_filled_fields(values, required_fields) == len(required_fields):
            completed += 1
    return completed


def load_traceability_matrix(spec: dict[str, Any], trace_key: str) -> dict[str, Any]:
    config = TRACEABILITY_ARTIFACTS[trace_key]
    path = artifact_path(spec, config["artifact_key"]) / config["filename"]
    result: dict[str, Any] = {
        "path": display_path(path),
        "exists": path.is_file(),
        "section": config["section"],
        "section_present": False,
        "row_count": 0,
        "capability_labels": {},
        "surface_labels": {},
        "reference_labels": {},
        "rows_by_key": {},
        "duplicate_keys": [],
        "invalid_rows": 0,
    }
    if not path.is_file():
        return result

    sections = level2_sections(path.read_text(encoding="utf-8"))
    section_lines = sections.get(config["section"], [])
    if section_lines:
        result["section_present"] = True
    _headers, rows = first_markdown_table(section_lines)
    result["row_count"] = len(rows)

    capability_labels: dict[str, str] = {}
    surface_labels: dict[str, str] = {}
    reference_labels: dict[str, str] = {}
    rows_by_key: dict[str, dict[str, str]] = {}
    duplicate_keys: list[str] = []
    invalid_rows = 0

    for index, row in enumerate(rows, start=1):
        trace_id = table_value_from_headers(row, config["trace_id_headers"])
        capability = table_value_from_headers(row, config["capability_headers"])
        surface = table_value_from_headers(row, config["surface_headers"])
        reference = table_value_from_headers(row, config["reference_headers"])
        trace_id_key = normalize_traceability_label(trace_id)
        capability_key = normalize_traceability_label(capability)
        row_key = trace_id_key or capability_key
        if not row_key:
            invalid_rows += 1
            continue
        if row_key in rows_by_key:
            duplicate_keys.append(trace_id or capability or f"row-{index}")
            continue

        rows_by_key[row_key] = {
            "key": row_key,
            "trace_id": trace_id,
            "capability": capability,
            "surface": surface,
            "reference": reference,
            "display_key": trace_id or capability or f"row-{index}",
        }
        if capability_key:
            capability_labels[capability_key] = capability
        surface_key = normalize_traceability_label(surface)
        if surface_key:
            surface_labels[surface_key] = surface
        reference_key = normalize_traceability_label(reference)
        if reference_key:
            reference_labels[reference_key] = reference

    result["capability_labels"] = capability_labels
    result["surface_labels"] = surface_labels
    result["reference_labels"] = reference_labels
    result["rows_by_key"] = rows_by_key
    result["duplicate_keys"] = sorted(duplicate_keys)
    result["invalid_rows"] = invalid_rows
    return result


def compare_traceability_pair(
    source_name: str,
    target_name: str,
    source_matrix: dict[str, Any],
    target_matrix: dict[str, Any],
    compare_references: bool,
) -> dict[str, Any]:
    issues: list[str] = []
    source_label = source_name.upper() if source_name != "plan" else "PLAN"
    target_label = target_name.upper() if target_name != "plan" else "PLAN"

    if not source_matrix["exists"]:
        issues.append(f"{source_label} traceability artifact is missing: {source_matrix['path']}.")
    elif not source_matrix["section_present"]:
        issues.append(f"{source_label} traceability section is missing: {source_matrix['section']}.")
    elif source_matrix["row_count"] == 0:
        issues.append(f"{source_label} traceability section has no populated rows.")

    if not target_matrix["exists"]:
        issues.append(f"{target_label} traceability artifact is missing: {target_matrix['path']}.")
    elif not target_matrix["section_present"]:
        issues.append(f"{target_label} traceability section is missing: {target_matrix['section']}.")
    elif target_matrix["row_count"] == 0:
        issues.append(f"{target_label} traceability section has no populated rows.")

    if not issues:
        if source_matrix.get("duplicate_keys"):
            issues.append(
                f"{source_label} traceability has duplicate row keys and should add stable Trace ID values: {summarize_labels(source_matrix['duplicate_keys'])}."
            )
        if target_matrix.get("duplicate_keys"):
            issues.append(
                f"{target_label} traceability has duplicate row keys and should add stable Trace ID values: {summarize_labels(target_matrix['duplicate_keys'])}."
            )
        if int(source_matrix.get("invalid_rows", 0)) > 0:
            issues.append(f"{source_label} traceability has rows missing both Trace ID and capability labels.")
        if int(target_matrix.get("invalid_rows", 0)) > 0:
            issues.append(f"{target_label} traceability has rows missing both Trace ID and capability labels.")

        source_rows = source_matrix.get("rows_by_key", {})
        target_rows = target_matrix.get("rows_by_key", {})
        missing_rows: list[str] = []
        capability_mismatches: list[str] = []
        surface_mismatches: list[str] = []
        reference_mismatches: list[str] = []

        for row_key, source_row in source_rows.items():
            target_row = target_rows.get(row_key)
            if target_row is None:
                missing_rows.append(source_row["display_key"])
                continue

            source_capability = normalize_traceability_label(source_row["capability"])
            target_capability = normalize_traceability_label(target_row["capability"])
            if source_capability and target_capability and source_capability != target_capability:
                capability_mismatches.append(
                    f"{source_row['display_key']} ({source_row['capability']} -> {target_row['capability']})"
                )

            source_surface = normalize_traceability_label(source_row["surface"])
            target_surface = normalize_traceability_label(target_row["surface"])
            if source_surface and target_surface and source_surface != target_surface:
                surface_mismatches.append(
                    f"{source_row['display_key']} ({source_row['surface']} -> {target_row['surface']})"
                )
            elif source_surface and not target_surface:
                surface_mismatches.append(f"{source_row['display_key']} ({source_row['surface']} -> missing)")

            if compare_references:
                source_reference = normalize_traceability_label(source_row["reference"])
                target_reference = normalize_traceability_label(target_row["reference"])
                if source_reference and target_reference and source_reference != target_reference:
                    reference_mismatches.append(
                        f"{source_row['display_key']} ({source_row['reference']} -> {target_row['reference']})"
                    )
                elif source_reference and not target_reference:
                    reference_mismatches.append(f"{source_row['display_key']} ({source_row['reference']} -> missing)")

        if missing_rows:
            issues.append(
                f"{target_label} traceability is missing source rows carried by {source_label}: {summarize_labels(missing_rows)}."
            )
        if capability_mismatches:
            issues.append(
                f"{target_label} traceability changes capability meaning relative to {source_label}: {summarize_labels(capability_mismatches)}."
            )
        if surface_mismatches:
            issues.append(
                f"{target_label} traceability changes primary surfaces relative to {source_label}: {summarize_labels(surface_mismatches)}."
            )
        if reference_mismatches:
            issues.append(
                f"{target_label} traceability changes research references relative to {source_label}: {summarize_labels(reference_mismatches)}."
            )

    return {
        "name": f"{source_name}-to-{target_name}",
        "source_path": source_matrix["path"],
        "target_path": target_matrix["path"],
        "source_section": source_matrix["section"],
        "target_section": target_matrix["section"],
        "issues": issues,
        "ready": not issues,
        "metrics": {
            "source_rows": source_matrix["row_count"],
            "target_rows": target_matrix["row_count"],
            "source_duplicate_keys": len(source_matrix.get("duplicate_keys", [])),
            "target_duplicate_keys": len(target_matrix.get("duplicate_keys", [])),
            "source_capabilities": len(source_matrix["capability_labels"]),
            "target_capabilities": len(target_matrix["capability_labels"]),
            "source_surfaces": len(source_matrix["surface_labels"]),
            "target_surfaces": len(target_matrix["surface_labels"]),
            "source_references": len(source_matrix["reference_labels"]),
            "target_references": len(target_matrix["reference_labels"]),
            "aligned_rows": len(set(source_matrix.get("rows_by_key", {}).keys()).intersection(target_matrix.get("rows_by_key", {}).keys())),
        },
    }


def build_traceability_checks(spec: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    comparisons = TRACEABILITY_COMPARISONS.get(phase, [])
    if not comparisons:
        return []

    loaded: dict[str, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    for source_name, target_name, compare_references in comparisons:
        if source_name not in loaded:
            loaded[source_name] = load_traceability_matrix(spec, source_name)
        if target_name not in loaded:
            loaded[target_name] = load_traceability_matrix(spec, target_name)
        checks.append(compare_traceability_pair(source_name, target_name, loaded[source_name], loaded[target_name], compare_references))
    return checks


def semantic_checks_for_artifact(path: Path, phase: str, sections: dict[str, list[str]]) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    metrics: dict[str, Any] = {}
    name = path.name

    if phase == "research" and name == "01-competitor-landscape.md":
        research_window = bullet_field_map(sections.get("Research Window", []))
        metrics["research_window_fields"] = count_filled_fields(research_window, ["Stores", "Countries", "Languages sampled", "Start date", "End date"])
        metrics["competitor_rows"] = len(table_data_rows(sections.get("Competitor Shortlist", []), phase))
        metrics["feature_surface_rows"] = len(table_data_rows(sections.get("Feature Surface Comparison", []), phase))
        metrics["metadata_rows"] = len(table_data_rows(sections.get("Metadata Snapshot", []), phase))
        metrics["monetization_rows"] = len(table_data_rows(sections.get("Monetization And Packaging", []), phase))
        metrics["regional_rows"] = len(table_data_rows(sections.get("Regional And Segment Signals", []), phase))
        metrics["scale_headroom_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scale Signals And Market Headroom", [])),
            ["Total demand or category headroom signal", "Evidence of cross-market repeatability", "Evidence of high-frequency usage", "Distribution or acquisition pattern", "Operational complexity signal"],
        )
        metrics["strategic_patterns_filled"] = count_filled_fields(bullet_field_map(sections.get("Observed Strategic Patterns", [])), ["Pattern 1", "Pattern 2", "Pattern 3", "Pattern 4", "Pattern 5"])
        metrics["gaps_filled"] = count_filled_fields(bullet_field_map(sections.get("Gaps To Investigate", [])), ["Gap 1", "Gap 2", "Gap 3"])
        metrics["raw_refs_filled"] = count_filled_fields(bullet_field_map(sections.get("Raw Data References", [])), ["Sensor Tower export", "Notes", "Additional links or screenshots"])
        if metrics["research_window_fields"] < 5:
            issues.append("Research Window should fully cover stores, countries, languages sampled, and date bounds.")
        if metrics["competitor_rows"] < 3:
            issues.append("Competitor Shortlist should include at least three meaningful competitors.")
        if metrics["feature_surface_rows"] < 3:
            issues.append("Feature Surface Comparison should compare at least three competitors.")
        if metrics["metadata_rows"] < 3:
            issues.append("Metadata Snapshot should include at least three populated metadata rows.")
        if metrics["monetization_rows"] < 2:
            issues.append("Monetization And Packaging should compare at least two competitors.")
        if metrics["regional_rows"] < 2:
            issues.append("Regional And Segment Signals should capture at least two market or segment observations.")
        if metrics["scale_headroom_fields"] < 4:
            issues.append("Scale Signals And Market Headroom should explain category headroom, repeatability, frequency, distribution, and operational complexity.")
        if metrics["strategic_patterns_filled"] < 4:
            issues.append("Observed Strategic Patterns should capture at least four concrete patterns.")
        if metrics["gaps_filled"] < 3:
            issues.append("Gaps To Investigate should capture at least three meaningful gaps.")
        if metrics["raw_refs_filled"] < 2:
            issues.append("Raw Data References should include exported evidence plus additional supporting notes or links.")

    if phase == "research" and name == "02-review-insights.md":
        query_context = bullet_field_map(sections.get("Query Context", []))
        metrics["query_context_fields"] = count_filled_fields(query_context, ["Apps reviewed", "Countries", "Languages reviewed", "Date window", "Total reviews", "Regional coverage rationale"])
        metrics["complaint_rows"] = len(table_data_rows(sections.get("Top Complaint Clusters", []), phase))
        metrics["delight_rows"] = len(table_data_rows(sections.get("Top Delight Clusters", []), phase))
        metrics["job_rows"] = len(table_data_rows(sections.get("Jobs Users Are Hiring The Product To Do", []), phase))
        metrics["request_rows"] = len(table_data_rows(sections.get("Explicit Feature Requests", []), phase))
        metrics["anti_feature_rows"] = len(table_data_rows(sections.get("Anti-Features", []), phase))
        metrics["persona_rows"] = len(table_data_rows(sections.get("Persona Or Segment Breakdowns", []), phase))
        metrics["hotspots_filled"] = count_filled_fields(bullet_field_map(sections.get("Version Or Country Hotspots", [])), ["Hotspot 1", "Hotspot 2", "Hotspot 3"])
        metrics["raw_refs_filled"] = count_filled_fields(bullet_field_map(sections.get("Raw Data References", [])), ["Review export", "Review insight report", "Sample review evidence file"])
        if metrics["query_context_fields"] < 6:
            issues.append("Query Context should identify apps, countries, languages, date window, review volume, and global coverage rationale.")
        if metrics["complaint_rows"] < 3 or metrics["delight_rows"] < 2:
            issues.append("Review insights should include multiple complaint clusters and multiple delight clusters.")
        if metrics["job_rows"] < 2:
            issues.append("Review insights should identify at least two jobs users are hiring the product to do.")
        if metrics["request_rows"] < 3 or metrics["anti_feature_rows"] < 2:
            issues.append("Review insights should capture multiple explicit feature requests and anti-features.")
        if metrics["persona_rows"] < 2:
            issues.append("Persona Or Segment Breakdowns should cover at least two user segments.")
        if metrics["hotspots_filled"] < 2:
            issues.append("Version Or Country Hotspots should capture at least two concrete hotspots.")
        if metrics["raw_refs_filled"] < 2:
            issues.append("Review insights should reference raw review exports plus a derived report or sample evidence file.")

    if phase == "research" and name == "03-feature-opportunities.md":
        metrics["must_have_rows"] = len(table_data_rows(sections.get("Must-Have Features", []), phase))
        metrics["capability_map_rows"] = len(table_data_rows(sections.get("Prioritized Capability Map", []), phase))
        metrics["differentiator_rows"] = len(table_data_rows(sections.get("Differentiators", []), phase))
        metrics["avoidance_rows"] = len(table_data_rows(sections.get("Avoidances", []), phase))
        metrics["hypothesis_rows"] = len(table_data_rows(sections.get("Open Hypotheses", []), phase))
        scope_lines = sections.get("Scope Recommendation", [])
        metrics["scope_recommendation_fields"] = count_filled_fields(
            bullet_field_map(scope_lines),
            ["Core outcomes", "Why now", "Expansion outcomes", "Why later", "Strategic bets", "Validation dependency"],
        )
        metrics["recommendation_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Recommendation", [])),
            ["Core feature set", "First premium lever", "Biggest UX risk", "Biggest market risk", "Biggest retention lever", "Biggest trust or quality requirement"],
        )
        metrics["growth_scale_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Growth And Scale Recommendation", [])),
            ["Primary growth loop", "Primary retention loop", "Main global expansion lever", "Main operational constraint at scale", "Why this can plausibly reach 10M DAU"],
        )
        if metrics["must_have_rows"] < 4:
            issues.append("Must-Have Features should include at least four evidence-backed rows.")
        if metrics["capability_map_rows"] < 5:
            issues.append("Prioritized Capability Map should contain at least five capabilities.")
        if min(metrics["differentiator_rows"], metrics["avoidance_rows"], metrics["hypothesis_rows"]) < 2:
            issues.append("Feature opportunities should cover multiple differentiators, avoidances, and open hypotheses.")
        if metrics["scope_recommendation_fields"] < 6:
            issues.append("Scope Recommendation should describe V1, V1.5, and V2 with concrete staged rationale.")
        if metrics["recommendation_fields"] < 6:
            issues.append("Recommendation should summarize feature set, monetization, retention, and trust or quality implications.")
        if metrics["growth_scale_fields"] < 4:
            issues.append("Growth And Scale Recommendation should define growth, retention, expansion, and scale viability rather than stopping at feature scope.")

    if phase == "prd" and name == "product-requirements.md":
        metrics["journey_count"] = len(numbered_item_values(sections.get("Core User Journeys", [])))
        metrics["core_capability_rows"] = len(table_data_rows(sections.get("Feature System", []), phase))
        metrics["functional_requirement_rows"] = len(table_data_rows(sections.get("Functional Requirements", []), phase))
        metrics["risk_rows"] = len(table_data_rows(sections.get("Risks", []), phase))
        metrics["goal_fields"] = count_filled_fields(bullet_field_map(sections.get("Product Goals", [])), ["Goal 1", "Goal 2", "Goal 3", "Goal 4"])
        metrics["non_goal_fields"] = count_filled_fields(bullet_field_map(sections.get("Non-Goals", [])), ["Non-goal 1", "Non-goal 2", "Non-goal 3"])
        metrics["summary_fields"] = count_filled_fields(bullet_field_map(sections.get("Product Summary", [])), ["One-line concept", "Product category", "Target market", "Why this product wins now"])
        metrics["problem_fields"] = count_filled_fields(bullet_field_map(sections.get("Problem Statement", [])), ["Primary user problem", "Why current solutions fall short", "Most common user complaints from research"])
        metrics["market_synthesis_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Market And Research Synthesis", [])),
            ["Competitors covered", "Review volume covered", "Key global patterns", "Key regional differences", "What users consistently love", "What users consistently hate", "Evidence confidence"],
        )
        metrics["experience_principles_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Experience Principles", [])),
            ["Principle 1", "Principle 2", "Principle 3", "Principle 4"],
        )
        metrics["localization_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Localization Requirements", [])),
            ["Source language", "Target locales", "Localization system", "Translation workflow"],
        )
        metrics["business_model_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Business Model", [])),
            ["Monetization approach", "Pricing assumptions", "Paywall or upgrade moments", "Revenue risks"],
        )
        metrics["growth_system_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Growth System", [])),
            ["Primary acquisition loops", "Activation strategy", "Retention loops", "Referral / network / distribution hooks", "Experimentation surfaces"],
        )
        metrics["launch_scope_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Launch Scope And Sequencing", [])),
            ["In scope", "Out of scope", "Success bar", "Dependency", "Strategic expansion", "Validation required first"],
        )
        metrics["trust_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Operational And Trust Requirements", [])),
            ["Privacy or compliance constraints", "Moderation / abuse / fraud concerns", "Reliability expectations", "Customer support or feedback loop"],
        )
        metrics["scale_readiness_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scale Readiness Requirements", [])),
            ["Target scale assumption", "Performance and latency expectations", "Abuse / fraud / moderation model", "Analytics and experimentation instrumentation", "Operational ownership and on-call expectation"],
        )
        metrics["traceability_rows"] = len(table_data_rows(sections.get("Cross-Phase Traceability Matrix", []), phase))
        metrics["evidence_appendix_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Evidence Appendix", [])),
            ["Competitor landscape", "Review insights", "Feature opportunities", "Key review quotes or themes file", "Additional market notes"],
        )
        if metrics["summary_fields"] < 4:
            issues.append("Product Summary should define concept, category, market, and why the product wins now.")
        if metrics["problem_fields"] < 3:
            issues.append("Problem Statement should connect the user problem to concrete research-backed complaints.")
        if metrics["market_synthesis_fields"] < 6:
            issues.append("Market And Research Synthesis should summarize competitor coverage, review coverage, global patterns, and global user likes and dislikes.")
        if metrics["journey_count"] < 4:
            issues.append("PRD should describe at least four concrete user journeys.")
        if metrics["core_capability_rows"] < 6:
            issues.append("Feature System should capture a sufficiently rich product capability set.")
        if metrics["functional_requirement_rows"] < 8:
            issues.append("Functional Requirements needs a materially richer requirement set than a demo PRD.")
        if metrics["risk_rows"] < 3:
            issues.append("Risks should cover at least three meaningful product or delivery risks.")
        if metrics["goal_fields"] < 3:
            issues.append("Product Goals should include at least three concrete goals.")
        if metrics["experience_principles_fields"] < 3:
            issues.append("Experience Principles should define at least three concrete product principles.")
        if metrics["localization_fields"] < 4:
            issues.append("Localization Requirements should fill source language, target locales, system, and workflow.")
        if metrics["business_model_fields"] < 3:
            issues.append("Business Model should define monetization, pricing assumptions, and upgrade logic.")
        if metrics["growth_system_fields"] < 4:
            issues.append("Growth System should define acquisition, activation, retention, and experimentation surfaces for a scaled product.")
        if metrics["launch_scope_fields"] < 4:
            issues.append("Launch Scope And Sequencing should define a staged release plan beyond a single demo release.")
        if metrics["trust_fields"] < 3:
            issues.append("Operational And Trust Requirements should cover reliability, trust, and support expectations.")
        if metrics["scale_readiness_fields"] < 4:
            issues.append("Scale Readiness Requirements should define target scale, performance, abuse controls, instrumentation, and operational ownership.")
        if metrics["traceability_rows"] < 4:
            issues.append("Cross-Phase Traceability Matrix should map at least four research-backed capabilities through design, delivery, and release.")
        if metrics["evidence_appendix_fields"] < 4:
            issues.append("Evidence Appendix should point back to research artifacts and richer supporting evidence.")

    if phase == "design" and name == "ui-ux-spec.md":
        metrics["design_context_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Design Context", [])),
            ["Target audience", "Use cases", "Brand tone", "Differentiation goal", "Product maturity target"],
        )
        metrics["experience_strategy_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Product Experience Strategy", [])),
            ["Primary promise to the user", "Emotional tone", "Trust-building strategy", "Key moments that must feel premium"],
        )
        metrics["visual_direction_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Visual Direction", [])),
            ["Aesthetic direction", "Typography system", "Color system", "Motion principles", "Density and spacing strategy"],
        )
        metrics["readability_rule_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Accessibility And Readability Rules", [])),
            ["Minimum contrast expectations", "CTA readability rules", "Disabled/loading state rules", "Focus state rules", "Touch target and mobile ergonomics rules"],
        )
        metrics["localization_rule_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Localization And Copy Rules", [])),
            ["Source locale", "Target locales", "Long-text expansion and multi-locale layout considerations", "Tone and terminology rules"],
        )
        metrics["ia_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Information Architecture", [])),
            ["Primary navigation", "Secondary navigation", "Key page groups", "Entry points and conversion paths"],
        )
        metrics["flow_coverage_fields"] = count_filled_fields(
            bullet_field_map(sections.get("User Flow Coverage", [])),
            ["Acquisition or entry flow", "Activation flow", "Core repeat-use flow", "Upgrade / conversion flow", "Recovery or support flow"],
        )
        metrics["component_rule_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Component Rules", [])),
            ["Buttons", "Forms", "Cards", "Lists", "Modals", "Navigation", "Data visualization or rich content"],
        )
        metrics["page_blocks_completed"] = complete_page_blocks(sections.get("Page Specs", []))
        metrics["state_matrix_rows"] = len(table_data_rows(sections.get("State Matrix", []), phase))
        metrics["deep_dive_blocks_completed"] = complete_named_blocks(
            sections.get("Key Journey Surface Deep Dives", []),
            [
                "Journey stage",
                "User intent",
                "Major modules",
                "State strategy",
                "Trust or support cues",
                "Conversion or retention role",
                "Localization or market adaptation notes",
            ],
        )
        metrics["design_system_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Design System Definition", [])),
            [
                "Foundation tokens",
                "Component hierarchy and reuse model",
                "Iconography, illustration, or media direction",
                "Surface, elevation, and container treatment",
                "Data density and scannability rules",
            ],
        )
        metrics["responsive_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Responsive And Platform Behavior", [])),
            ["Mobile adaptation rules", "Tablet / desktop rules", "Input mode differences", "Performance or motion constraints"],
        )
        metrics["interaction_motion_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Interaction And Motion Details", [])),
            [
                "Transition and choreography rules",
                "Feedback and acknowledgement rules",
                "Form, validation, and input behavior",
                "Latency masking and perceived performance tactics",
                "Gesture, keyboard, and accessibility interaction notes",
            ],
        )
        metrics["trust_feedback_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Trust And Feedback Cues", [])),
            ["Security / privacy cues", "Progress feedback", "Error recovery guidance", "Empty-state education"],
        )
        metrics["scale_ux_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scale UX Requirements", [])),
            ["Onboarding for broad-market conversion", "Habit / repeat-use surfaces", "Power-user efficiency surfaces", "Localization and market adaptation surfaces", "Support / trust / abuse-reporting entry points"],
        )
        metrics["conversion_retention_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Conversion And Retention Surfaces", [])),
            [
                "First-run and onboarding surfaces",
                "Habit loop reinforcement surfaces",
                "Upgrade or premium presentation rules",
                "Re-engagement or win-back surfaces",
                "Referral, sharing, or collaboration surfaces",
            ],
        )
        metrics["impeccable_review_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Impeccable Review Notes", [])),
            [
                "Foundation directions explored",
                "Commands or workflows used",
                "Audit findings",
                "Critique findings",
                "Polish actions",
                "Anti-patterns explicitly avoided",
                "Remaining design debt or open tensions",
            ],
        )
        metrics["traceability_rows"] = len(table_data_rows(sections.get("Traceability To Research And PRD", []), phase))
        if metrics["design_context_fields"] < 4:
            issues.append("UI UX spec should define audience, use cases, brand tone, and product maturity target.")
        if metrics["experience_strategy_fields"] < 4:
            issues.append("UI UX spec should define the product experience strategy, including premium and trust moments.")
        if metrics["visual_direction_fields"] < 5:
            issues.append("UI UX spec should fully define aesthetic, typography, color, motion, and spacing strategy.")
        if metrics["readability_rule_fields"] < 4:
            issues.append("UI UX spec should define all readability and accessibility rules.")
        if metrics["localization_rule_fields"] < 4:
            issues.append("Localization And Copy Rules should define locale scope, expansion behavior, and terminology rules.")
        if metrics["ia_fields"] < 4:
            issues.append("Information Architecture should cover navigation, page groups, and conversion paths.")
        if metrics["flow_coverage_fields"] < 4:
            issues.append("User Flow Coverage should cover acquisition, activation, repeat use, and recovery.")
        if metrics["page_blocks_completed"] < 3:
            issues.append("UI UX spec should contain at least three fully filled page specs.")
        if metrics["state_matrix_rows"] < 3:
            issues.append("State Matrix should cover at least three key surfaces with edge states.")
        if metrics["deep_dive_blocks_completed"] < 3:
            issues.append("Key Journey Surface Deep Dives should capture at least three high-value surfaces with state, trust, retention, and localization detail.")
        if metrics["design_system_fields"] < 4:
            issues.append("Design System Definition should define foundation tokens, reuse, media direction, surfaces, and scannability rules.")
        if metrics["component_rule_fields"] < 5:
            issues.append("Component Rules should cover most core component families and richer content surfaces.")
        if metrics["responsive_fields"] < 4:
            issues.append("Responsive And Platform Behavior should define mobile, larger-screen, and input-mode adaptations.")
        if metrics["interaction_motion_fields"] < 4:
            issues.append("Interaction And Motion Details should define choreography, input behavior, and perceived-performance tactics.")
        if metrics["trust_feedback_fields"] < 3:
            issues.append("Trust And Feedback Cues should cover trust, progress, and recovery guidance.")
        if metrics["scale_ux_fields"] < 4:
            issues.append("Scale UX Requirements should cover onboarding, repeat use, power-user efficiency, localization adaptation, and trust or abuse entry points.")
        if metrics["conversion_retention_fields"] < 4:
            issues.append("Conversion And Retention Surfaces should define onboarding, habit loops, upgrade moments, and re-engagement surfaces.")
        if metrics["traceability_rows"] < 4:
            issues.append("Traceability To Research And PRD should map at least four launch-critical capabilities to concrete design surfaces.")
        if metrics["impeccable_review_fields"] < 5:
            issues.append("Impeccable Review Notes should capture foundation, workflow, critique, polish, and unresolved design tradeoffs.")

    if phase == "design" and name == "i18n-strategy.md":
        metrics["scope_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Localization Scope", [])),
            ["Product surfaces in scope", "Source locale", "Required target locales"],
        )
        metrics["locale_priority_rows"] = len(table_data_rows(sections.get("Locale Prioritization", []), phase))
        metrics["stack_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Stack And Resource Model", [])),
            ["Primary stack", "Localization resource location", "Translation helper or accessor", "Stack-specific notes"],
        )
        metrics["source_of_truth_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Source Of Truth", [])),
            ["Who owns source copy", "Key naming convention", "Placeholder and formatting rules", "Brand terms that must not be translated"],
        )
        metrics["copy_governance_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Copy Governance", [])),
            ["Source copy review owner", "Terminology review rule", "Fallback copy policy", "Release-time copy freeze rule"],
        )
        metrics["delivery_rule_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Delivery Rules", [])),
            ["Locale sync workflow", "Translation completion workflow", "Hardcoded copy check command", "Escalation rule for missing translations"],
        )
        metrics["layout_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Layout And UX Considerations", [])),
            ["Long text expansion risk", "RTL requirements", "Locale-specific formatting", "Accessibility considerations", "Screenshot or visual QA expectations"],
        )
        metrics["validation_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Validation", [])),
            ["Required locale coverage before release", "Manual QA locales", "Automated checks", "High-risk flows that must be tested in every required locale"],
        )
        if metrics["scope_fields"] < 3:
            issues.append("I18n Strategy should define scope, source locale, and required target locales.")
        if metrics["locale_priority_rows"] < 2:
            issues.append("Locale Prioritization should cover at least two locales or locale groups.")
        if metrics["stack_fields"] < 4:
            issues.append("I18n Strategy should define the stack resource location and translation accessor.")
        if metrics["copy_governance_fields"] < 3:
            issues.append("Copy Governance should define ownership, fallback policy, and release-time controls.")
        if metrics["delivery_rule_fields"] < 3:
            issues.append("I18n Strategy should define locale sync, translation workflow, and hardcoded copy checks.")
        if metrics["layout_fields"] < 4:
            issues.append("Layout And UX Considerations should cover expansion, RTL, formatting, and visual QA.")
        if metrics["validation_fields"] < 4:
            issues.append("I18n Strategy should define locale coverage, manual QA, and automated checks.")

    if phase in {"planning", "delivery"} and name == "implementation-plan.md":
        metrics["scope_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scope For This Plan", [])),
            ["Included", "Excluded"],
        )
        metrics["architecture_strategy_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Architecture And Technical Strategy", [])),
            ["Core implementation approach", "Key modules or services involved", "Data model or contract impact", "Technical risks to control early"],
        )
        metrics["milestone_rows"] = len(table_data_rows(sections.get("Milestones", []), phase))
        metrics["dependency_risk_rows"] = len(table_data_rows(sections.get("Dependency And Risk Map", []), phase))
        metrics["completed_batches"] = 0
        batch_lines = sections.get("Task Batches", [])
        batch_blocks: list[list[str]] = []
        current: list[str] = []
        for raw_line in batch_lines:
            if raw_line.strip().startswith("### "):
                if current:
                    batch_blocks.append(current)
                current = [raw_line]
                continue
            if current:
                current.append(raw_line)
        if current:
            batch_blocks.append(current)
        for block in batch_blocks:
            values = bullet_field_map(block)
            if count_filled_fields(values, ["Goal", "Dependencies", "Test-first tasks", "Verification"]) == 4:
                metrics["completed_batches"] += 1
        metrics["localization_work_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Localization Work", [])),
            ["Hardcoded string extraction tasks", "Source locale key creation", "Target locale sync", "Translation completion workflow"],
        )
        metrics["review_cadence_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Review And Verification Cadence", [])),
            ["When code review runs", "Required verification before each commit", "Batch completion evidence format", "When to update initiative artifacts"],
        )
        verification_commands = code_block_commands(sections.get("Verification Commands", []))
        metrics["verification_command_count"] = len(verification_commands)
        metrics["custom_verification_command_count"] = len([cmd for cmd in verification_commands if cmd != "./scripts/check-no-hardcoded-copy.sh"])
        metrics["commit_strategy_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Commit Strategy", [])),
            ["Commit frequency", "Branch strategy", "PR strategy"],
        )
        metrics["rollout_recovery_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Rollout And Recovery Plan", [])),
            ["Release unit for this work", "Rollback or recovery strategy", "Observability or monitoring checks", "Post-merge validation"],
        )
        metrics["scale_reliability_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scale And Reliability Workstreams", [])),
            ["Performance and capacity work", "Analytics and experimentation work", "Abuse / fraud / trust safeguards", "Observability and incident readiness", "Growth surface instrumentation"],
        )
        metrics["traceability_rows"] = len(table_data_rows(sections.get("Delivery Traceability Map", []), phase))
        if metrics["scope_fields"] < 2:
            issues.append("Implementation plan should define what is included and excluded.")
        if metrics["architecture_strategy_fields"] < 4:
            issues.append("Implementation plan should define the technical strategy, touched systems, and early risks.")
        if metrics["milestone_rows"] < 1:
            issues.append("Implementation plan needs at least one milestone row.")
        if metrics["dependency_risk_rows"] < 2:
            issues.append("Dependency And Risk Map should capture at least two concrete dependencies or risks.")
        if metrics["completed_batches"] < 2:
            issues.append("Implementation plan should contain at least two fully filled task batches.")
        if metrics["localization_work_fields"] < 4:
            issues.append("Implementation plan should define all localization work lanes.")
        if metrics["review_cadence_fields"] < 4:
            issues.append("Review And Verification Cadence should define review timing, verification rules, and artifact update timing.")
        if metrics["custom_verification_command_count"] < 2:
            issues.append("Verification Commands should include multiple project-specific commands beyond the default copy check.")
        if metrics["commit_strategy_fields"] < 3:
            issues.append("Commit Strategy should define commit frequency, branch strategy, and PR strategy.")
        if metrics["rollout_recovery_fields"] < 3:
            issues.append("Rollout And Recovery Plan should define release unit, rollback strategy, and post-merge checks.")
        if metrics["scale_reliability_fields"] < 4:
            issues.append("Scale And Reliability Workstreams should define performance, observability, trust, analytics, and growth instrumentation work.")
        if metrics["traceability_rows"] < 4:
            issues.append("Delivery Traceability Map should map at least four capabilities from PRD/design into delivery batches and verification.")

    if phase == "delivery" and name == "release-readiness.md":
        metrics["verification_summary_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Verification Summary", [])),
            ["Test status", "Build status", "Lint status", "Manual QA status"],
        )
        metrics["ux_audit_fields"] = count_filled_fields(
            bullet_field_map(sections.get("UX Audit Summary", [])),
            [
                "Final impeccable audit",
                "Contrast and readability checks",
                "Responsive checks",
                "Interaction polish and feedback checks",
                "Trust and recovery cue checks",
                "Localization layout checks",
            ],
        )
        metrics["localization_summary_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Localization Summary", [])),
            ["Hardcoded copy audit", "Locale coverage", "Translation validation", "Hardcoded copy check command/result"],
        )
        metrics["operational_readiness_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Operational Readiness", [])),
            ["Logging / monitoring readiness", "Support readiness", "Incident owner or escalation path", "Data / analytics readiness"],
        )
        metrics["rollback_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Rollout And Rollback Plan", [])),
            ["Rollout strategy", "Rollback trigger", "Rollback owner", "Kill switch or mitigation notes"],
        )
        metrics["scale_launch_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scale Launch Controls", [])),
            ["Capacity / traffic assumption", "Feature flag or staged rollout controls", "Incident drill or rollback rehearsal", "Support / moderation readiness", "Analytics dashboard owner"],
        )
        metrics["watchlist_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Post-Launch Watchlist", [])),
            ["Activation signal to watch", "Retention signal to watch", "Revenue or conversion signal to watch", "Quality or support signal to watch"],
        )
        metrics["traceability_rows"] = len(table_data_rows(sections.get("Delivered Traceability Summary", []), phase))
        if metrics["verification_summary_fields"] < 2:
            issues.append("Delivery should already update Verification Summary with meaningful implementation evidence.")
        if metrics["ux_audit_fields"] < 3:
            issues.append("Delivery should already record a substantial impeccable-driven UX audit before release.")
        if metrics["localization_summary_fields"] < 2:
            issues.append("Delivery should update Localization Summary with actual locale and hardcoded-copy evidence.")
        if metrics["operational_readiness_fields"] < 3:
            issues.append("Delivery should update Operational Readiness with monitoring, support, and analytics ownership.")
        if metrics["rollback_fields"] < 2:
            issues.append("Delivery should update Rollout And Rollback Plan before release certification.")
        if metrics["scale_launch_fields"] < 3:
            issues.append("Delivery should update Scale Launch Controls with traffic, rollout, and support assumptions.")
        if metrics["watchlist_fields"] < 3:
            issues.append("Delivery should define an initial post-launch watchlist before delivery is certified.")
        if metrics["traceability_rows"] < 4:
            issues.append("Delivered Traceability Summary should map at least four shipped capabilities to their design surfaces and release checks.")

    if phase == "release" and name == "release-readiness.md":
        metrics["verification_summary_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Verification Summary", [])),
            ["Test status", "Build status", "Lint status", "Manual QA status"],
        )
        metrics["ux_audit_fields"] = count_filled_fields(
            bullet_field_map(sections.get("UX Audit Summary", [])),
            [
                "Final impeccable audit",
                "Contrast and readability checks",
                "Responsive checks",
                "Interaction polish and feedback checks",
                "Trust and recovery cue checks",
                "Localization layout checks",
            ],
        )
        metrics["localization_summary_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Localization Summary", [])),
            ["Hardcoded copy audit", "Locale coverage", "Translation validation", "Hardcoded copy check command/result"],
        )
        metrics["operational_readiness_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Operational Readiness", [])),
            ["Logging / monitoring readiness", "Support readiness", "Incident owner or escalation path", "Data / analytics readiness"],
        )
        checked, total = checkbox_counts(sections.get("Release Checklist", []))
        metrics["release_checklist_checked"] = checked
        metrics["release_checklist_total"] = total
        metrics["known_issue_rows"] = len(table_data_rows(sections.get("Known Issues", []), phase))
        metrics["rollback_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Rollout And Rollback Plan", [])),
            ["Rollout strategy", "Rollback trigger", "Rollback owner", "Kill switch or mitigation notes"],
        )
        metrics["scale_launch_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Scale Launch Controls", [])),
            ["Capacity / traffic assumption", "Feature flag or staged rollout controls", "Incident drill or rollback rehearsal", "Support / moderation readiness", "Analytics dashboard owner"],
        )
        metrics["watchlist_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Post-Launch Watchlist", [])),
            ["Activation signal to watch", "Retention signal to watch", "Revenue or conversion signal to watch", "Quality or support signal to watch"],
        )
        metrics["release_notes_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Release Notes Draft", [])),
            ["Added", "Improved", "Fixed"],
        )
        metrics["go_no_go_fields"] = count_filled_fields(
            bullet_field_map(sections.get("Go Or No-Go Rationale", [])),
            ["Reasons to ship", "Remaining risks", "Final recommendation"],
        )
        metrics["traceability_rows"] = len(table_data_rows(sections.get("Delivered Traceability Summary", []), phase))
        if metrics["verification_summary_fields"] < 4:
            issues.append("Release readiness should fill test/build/lint/manual QA status.")
        if metrics["ux_audit_fields"] < 5:
            issues.append("Release readiness should summarize final UX audit depth across readability, responsiveness, interaction polish, trust cues, and localization layout.")
        if metrics["localization_summary_fields"] < 4:
            issues.append("Release readiness should summarize locale coverage and hardcoded-copy validation.")
        if metrics["operational_readiness_fields"] < 4:
            issues.append("Release readiness should define monitoring, support, escalation, and analytics readiness.")
        if total > 0 and checked < total:
            issues.append("Release checklist is not fully checked yet.")
        if metrics["known_issue_rows"] < 1:
            issues.append("Known Issues should record at least one concrete issue or explicitly track a no-blocker state.")
        if metrics["rollback_fields"] < 3:
            issues.append("Rollout And Rollback Plan should define rollout, rollback trigger, and ownership.")
        if metrics["scale_launch_fields"] < 4:
            issues.append("Scale Launch Controls should define traffic assumptions, staged rollout controls, incident rehearsal, support readiness, and analytics ownership.")
        if metrics["watchlist_fields"] < 4:
            issues.append("Post-Launch Watchlist should define activation, retention, revenue, and quality watch signals.")
        if metrics["traceability_rows"] < 4:
            issues.append("Delivered Traceability Summary should map launch-critical capabilities to shipped evidence and release verification.")
        if metrics["release_notes_fields"] < 2:
            issues.append("Release notes draft should contain more than a token-level summary.")
        if metrics["go_no_go_fields"] < 3:
            issues.append("Go Or No-Go Rationale should explain why to ship, what risks remain, and the final recommendation.")

    return issues, metrics


def level2_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", raw_line)
        if heading:
            current = heading.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(raw_line)
    return sections


def inspect_artifact_readiness(path: Path, phase: str, expected_sections: list[str]) -> dict[str, Any]:
    if not path.is_file():
        return {
            "path": display_path(path),
            "exists": False,
            "missing_sections": expected_sections,
            "thin_sections": [],
            "placeholder_count": 0,
            "semantic_issues": [],
            "semantic_metrics": {},
            "ready": False,
        }

    text = path.read_text(encoding="utf-8")
    sections = level2_sections(text)
    missing_sections: list[str] = []
    thin_sections: list[str] = []
    placeholder_count = 0

    for line in text.splitlines():
        stripped = line.strip()
        if stripped and is_placeholder_line(stripped, phase):
            placeholder_count += 1

    for section in expected_sections:
        if section not in sections:
            missing_sections.append(section)
            continue
        if useful_content_count(sections[section], phase) == 0:
            thin_sections.append(section)

    semantic_issues, semantic_metrics = semantic_checks_for_artifact(path, phase, sections)

    return {
        "path": display_path(path),
        "exists": True,
        "missing_sections": missing_sections,
        "thin_sections": thin_sections,
        "placeholder_count": placeholder_count,
        "semantic_issues": semantic_issues,
        "semantic_metrics": semantic_metrics,
        "ready": not missing_sections and not thin_sections and placeholder_count == 0 and not semantic_issues,
    }


def build_phase_readiness(spec: dict[str, Any], phase: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    targets = phase_targets(spec, phase)
    if phase == "delivery":
        targets = [*targets, artifact_path(spec, "release_dir") / "release-readiness.md"]
    for target in targets:
        expected_sections = SECTION_EXPECTATIONS.get(phase, {}).get(target.name, [])
        checks.append(inspect_artifact_readiness(target, phase, expected_sections))

    traceability_checks = build_traceability_checks(spec, phase)
    total_missing = sum(len(check["missing_sections"]) for check in checks)
    total_thin = sum(len(check["thin_sections"]) for check in checks)
    total_placeholders = sum(int(check["placeholder_count"]) for check in checks)
    total_semantic_issues = sum(len(check.get("semantic_issues", [])) for check in checks)
    total_traceability_issues = sum(len(check.get("issues", [])) for check in traceability_checks)
    ready = all(bool(check["ready"]) for check in checks) and total_traceability_issues == 0

    if ready:
        summary = f"{phase} artifacts appear structurally and semantically ready for certification."
    else:
        summary = (
            f"{phase} artifacts still have {total_missing} missing sections, "
            f"{total_thin} thin sections, {total_placeholders} unresolved placeholder lines, "
            f"{total_semantic_issues} semantic readiness issues, and {total_traceability_issues} cross-phase traceability issues."
        )

    return {
        "phase": phase,
        "ready_for_certification": ready,
        "artifact_checks": checks,
        "traceability_checks": traceability_checks,
        "total_missing_sections": total_missing,
        "total_thin_sections": total_thin,
        "total_placeholders": total_placeholders,
        "total_semantic_issues": total_semantic_issues,
        "total_traceability_issues": total_traceability_issues,
        "summary": summary,
    }


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
        "artifacts_updated": evidence_artifacts[:],
        "commands_run": commands_run,
        "tests_run": tests_run,
        "validated_batches_completed": 0,
        "batch_commits": [],
        "workflow_trace": normalize_workflow_trace({}),
        "loop_execution": normalize_loop_execution({}),
        "recommended_result_status": recommended_result_status,
        "recommended_gate_action": recommended_gate_action,
        "recommended_gate_status": default_gate_status(phase) if recommended_gate_action in {"certify", "advance"} else "",
        "follow_up": follow_up,
    }


def git_state(project_dir: Path) -> dict[str, Any]:
    try:
        top_level = subprocess.run(
            ["git", "-C", str(project_dir), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return {"is_repo": False}

    head = ""
    branch = ""
    try:
        head = subprocess.run(
            ["git", "-C", str(project_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        head = ""
    try:
        branch = subprocess.run(
            ["git", "-C", str(project_dir), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        branch = ""

    dirty = bool(
        subprocess.run(
            ["git", "-C", str(project_dir), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {
        "is_repo": True,
        "top_level": top_level,
        "head": head,
        "branch": branch,
        "dirty": dirty,
    }


def commits_created(project_dir: Path, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    if not before.get("is_repo") or not after.get("is_repo"):
        return []
    before_head = ensure_string(before.get("head"))
    after_head = ensure_string(after.get("head"))
    if not after_head or before_head == after_head:
        return []
    revision = after_head if not before_head else f"{before_head}..{after_head}"
    try:
        output = subprocess.run(
            ["git", "-C", str(project_dir), "log", "--format=%H %s", revision],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def changed_files_in_commits(project_dir: Path, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    if not before.get("is_repo") or not after.get("is_repo"):
        return []
    before_head = ensure_string(before.get("head"))
    after_head = ensure_string(after.get("head"))
    if not after_head or before_head == after_head:
        return []
    if before_head:
        command = ["git", "-C", str(project_dir), "diff", "--name-only", f"{before_head}..{after_head}"]
    else:
        command = ["git", "-C", str(project_dir), "diff-tree", "--no-commit-id", "--name-only", "-r", after_head]
    try:
        output = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def is_workflow_artifact_path(path_value: str) -> bool:
    normalized = ensure_string(path_value).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return False
    for prefix in [".supernb/", ".claude/"]:
        if normalized == prefix[:-1] or normalized.startswith(prefix):
            return True
    return False


def delivery_workspace_change_findings(project_dir: Path, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changed_files = changed_files_in_commits(project_dir, before, after)
    if not changed_files:
        return []
    if any(not is_workflow_artifact_path(path) for path in changed_files):
        return []
    return [
        "Delivery batch did not modify any product workspace files outside .supernb/.claude workflow artifacts. "
        f"Changed files: {', '.join(changed_files)}"
    ]


def workflow_trace_findings(phase: str, report: dict[str, Any], commit_lines: list[str]) -> list[str]:
    issues: list[str] = []
    trace = report.get("workflow_trace") or {}
    for key in WORKFLOW_TRACE_KEYS:
        entry = trace.get(key)
        if not isinstance(entry, dict) or entry.get("used") is None:
            issues.append(f"workflow_trace is missing an explicit used=true/false entry for {key}.")
            continue
        if not ensure_string(entry.get("evidence")):
            issues.append(f"workflow_trace is missing evidence text for {key}.")

    if phase == "planning":
        if not (trace.get("writing_plans") or {}).get("used"):
            issues.append("Planning runs must use superpowers writing-plans.")
    if phase == "delivery":
        for required in ["writing_plans", "test_driven_development", "code_review", "subagent_or_executing_plans"]:
            if not (trace.get(required) or {}).get("used"):
                issues.append(f"Delivery runs must report {required}=true in workflow_trace.")
        if int(report.get("validated_batches_completed", 0) or 0) < 1:
            issues.append("Delivery runs must complete at least one validated batch.")
        batch_commits = ensure_list(report.get("batch_commits"))
        if not batch_commits and commit_lines:
            report["batch_commits"] = commit_lines
            batch_commits = commit_lines
        if not batch_commits:
            issues.append("Delivery runs must record at least one batch commit.")
    return issues


def loop_execution_findings(
    phase: str,
    harness: str,
    report: dict[str, Any],
    project_dir: Path,
    packet_dir: Path,
    response_text: str,
) -> list[str]:
    if phase not in LOOP_REQUIRED_PHASES or harness not in CLAUDE_LOOP_HARNESSES:
        return []

    loop_execution = report.get("loop_execution") or {}
    issues: list[str] = []
    used = loop_execution.get("used")
    mode = ensure_string(loop_execution.get("mode")).lower()
    completion_promise = ensure_string(loop_execution.get("completion_promise"))
    state_file = ensure_string(loop_execution.get("state_file"))
    max_iterations = int(loop_execution.get("max_iterations", 0) or 0)
    final_iteration = int(loop_execution.get("final_iteration", 0) or 0)
    exit_reason = ensure_string(loop_execution.get("exit_reason"))
    evidence = ensure_string(loop_execution.get("evidence"))

    if used is not True:
        issues.append(
            f"{phase.capitalize()} runs on Claude Code must use Ralph Loop instead of relying on self-judged completion. "
            "Switch to a loop-enabled Claude Code environment or treat the packet as needs-follow-up."
        )
        return issues
    if mode not in {"ralph-loop", "frad-superpower-loop", "superpower-loop"}:
        issues.append("loop_execution.mode must identify Ralph Loop for Claude Code planning and delivery runs.")
    if not completion_promise:
        issues.append("loop_execution.completion_promise is required for Claude Code planning and delivery runs.")
    if not state_file:
        issues.append("loop_execution.state_file is required for Claude Code planning and delivery runs.")
    if max_iterations < 1:
        issues.append("loop_execution.max_iterations must be a positive integer.")
    if final_iteration < 1:
        issues.append("loop_execution.final_iteration must record the last completed iteration.")
    if not exit_reason:
        issues.append("loop_execution.exit_reason must explain why the loop stopped.")
    if not evidence:
        issues.append("loop_execution.evidence must explain the Ralph Loop state or observed stop condition.")
    audit_summary, audit_path = resolve_loop_audit_summary(project_dir, packet_dir, report)
    if not audit_summary:
        issues.append(f"loop_execution.evidence must point to a valid Ralph Loop audit summary JSON. Got: {audit_path or '<missing>'}")
        return issues

    if ensure_string(audit_summary.get("completion_promise")) != completion_promise:
        issues.append("Ralph Loop audit summary completion_promise does not match loop_execution.completion_promise.")
    if ensure_string(audit_summary.get("state_file")) != state_file:
        issues.append("Ralph Loop audit summary state_file does not match loop_execution.state_file.")
    expected_session = ensure_string(audit_summary.get("expected_session_id"))
    observed_session = ensure_string(audit_summary.get("last_session_id"))
    if not audit_summary.get("state_observed"):
        issues.append("Ralph Loop audit summary never observed the state file.")
    if not audit_summary.get("removed_after_observation"):
        issues.append("Ralph Loop audit summary did not observe the state file being removed, so loop completion is unverified.")
    if ensure_string(audit_summary.get("final_status")) != "state_removed":
        issues.append("Ralph Loop audit summary final_status must be state_removed.")
    last_iteration = int(audit_summary.get("last_iteration", 0) or 0)
    if last_iteration < 1:
        issues.append("Ralph Loop audit summary must record at least one observed iteration.")
    if final_iteration > last_iteration:
        issues.append("loop_execution.final_iteration cannot exceed the last iteration recorded by the audit summary.")
    if harness == "claude-code-prompt":
        if not expected_session:
            issues.append("Prompt-first Ralph Loop audit summary must record the expected Claude session id.")
        elif observed_session != expected_session:
            issues.append("Prompt-first Ralph Loop audit summary session id does not match the active Claude session.")
    if harness == "claude-code":
        if not expected_session:
            issues.append("Direct Claude Code Ralph Loop audit summary must record the generated Claude session id.")
        elif observed_session != expected_session:
            issues.append("Direct Claude Code Ralph Loop audit summary session id does not match the generated Claude session.")
        promise_text = extract_promise_text(response_text)
        if promise_text != completion_promise:
            issues.append("Direct Claude Code execution must end with the exact Ralph Loop completion promise tag.")
    return issues


def evidence_artifact_findings(project_dir: Path, packet_dir: Path, report: dict[str, Any], response_text: str, stderr_text: str) -> list[str]:
    issues: list[str] = []
    combined_output = "\n".join([response_text, stderr_text])

    for command in ensure_list(report.get("tests_run")):
        if command not in combined_output and command not in response_text:
            issues.append(f"tests_run entry is not reflected in captured output: {command}")

    for artifact in ensure_list(report.get("evidence_artifacts")):
        artifact_path = Path(artifact).expanduser()
        candidates = [artifact_path]
        if not artifact_path.is_absolute():
            candidates.extend([(project_dir / artifact_path).resolve(), (packet_dir / artifact_path).resolve()])
        if not any(candidate.exists() for candidate in candidates):
            issues.append(f"evidence_artifact does not exist in project or packet scope: {artifact}")

    return issues


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
    project_dir: Path,
    phase_readiness: dict[str, Any],
    git_before: dict[str, Any],
    git_after: dict[str, Any],
    created_commits: list[str],
) -> dict[str, Any]:
    excerpt = short_text_excerpt(response_text)
    stderr_excerpt = short_text_excerpt(stderr_text)
    structured_report = extract_report_json(response_text)
    report_source = "structured-report" if structured_report else "heuristic"
    missing_structured_report = False

    if not structured_report:
        structured_report = heuristic_report_from_text(phase, status, response_text, stderr_text, excerpt, stderr_excerpt)
        if not dry_run and status in {"succeeded", "failed"} and harness in DIRECT_EXECUTION_HARNESSES:
            missing_structured_report = True
            report_source = "heuristic-missing-structured-report"

    if created_commits and not structured_report.get("batch_commits"):
        structured_report["batch_commits"] = created_commits

    workflow_issues = workflow_trace_findings(phase, structured_report, created_commits)
    workflow_issues.extend(loop_execution_findings(phase, harness, structured_report, project_dir, packet_dir, response_text))
    if missing_structured_report:
        workflow_issues.insert(0, missing_structured_report_issue(harness))
    workflow_issues.extend(evidence_artifact_findings(project_dir, packet_dir, structured_report, response_text, stderr_text))
    if phase == "delivery":
        workflow_issues.extend(delivery_workspace_change_findings(project_dir, git_before, git_after))
    commit_issue = ""
    if phase == "delivery" and git_after.get("is_repo") and not created_commits:
        commit_issue = "No new git commit was detected for this delivery batch."
        workflow_issues.append(commit_issue)

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
        if missing_structured_report:
            if result_status == "succeeded":
                result_status = "needs-follow-up"
            next_step = "rerun the batch with a compliant REPORT JSON block or import a structured manual packet before certification"
        elif workflow_issues:
            if result_status == "succeeded":
                result_status = "needs-follow-up"
            next_step = "apply the execution packet, then resolve the workflow-trace and commit-policy gaps"
        elif not phase_readiness.get("ready_for_certification", False):
            if result_status == "succeeded":
                result_status = "needs-follow-up"
            next_step = "apply the execution packet and address the phase-readiness gaps before certification"
        elif gate_action == "advance":
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
        "phase_readiness": phase_readiness,
        "workflow_issues": workflow_issues,
        "git_before": git_before,
        "git_after": git_after,
        "commits_created": created_commits,
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
        f"- Record result: `{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id {initiative_id} --packet {packet_dir}`",
        f"- Record result and certify: `{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id {initiative_id} --packet {packet_dir} --certify`",
        f"- Record result and certify+apply: `{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id {initiative_id} --packet {packet_dir} --apply-certification`",
        "",
        "## Evidence",
        "",
        f"- Packet summary: `{display_path(packet_dir / 'summary.md')}`",
        f"- Phase readiness: `{display_path(packet_dir / 'phase-readiness.md')}`",
        f"- Response: `{display_path(packet_dir / 'response.md')}`",
        f"- Stdout: `{display_path(packet_dir / 'stdout.log')}`",
        f"- Stderr: `{display_path(packet_dir / 'stderr.log')}`",
    ]
    report = suggestion.get("execution_report") or {}
    readiness = suggestion.get("phase_readiness") or {}
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
    if report.get("artifacts_updated"):
        lines.extend(["", "## Artifacts Updated", ""])
        for item in report["artifacts_updated"]:
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
    workflow_trace = report.get("workflow_trace") or {}
    if workflow_trace:
        lines.extend(["", "## Workflow Trace", ""])
        for key in WORKFLOW_TRACE_KEYS:
            entry = workflow_trace.get(key) or {}
            used = entry.get("used")
            used_text = "yes" if used is True else ("no" if used is False else "missing")
            lines.append(f"- `{key}` used=`{used_text}` evidence=`{entry.get('evidence', '')}`")
    loop_execution = report.get("loop_execution") or {}
    if any(loop_execution.values()):
        lines.extend(["", "## Loop Execution", ""])
        used = loop_execution.get("used")
        used_text = "yes" if used is True else ("no" if used is False else "missing")
        lines.append(f"- Used: `{used_text}`")
        lines.append(f"- Mode: `{loop_execution.get('mode', '')}`")
        lines.append(f"- Completion promise: `{loop_execution.get('completion_promise', '')}`")
        lines.append(f"- State file: `{loop_execution.get('state_file', '')}`")
        lines.append(f"- Max iterations: `{loop_execution.get('max_iterations', 0)}`")
        lines.append(f"- Final iteration: `{loop_execution.get('final_iteration', 0)}`")
        lines.append(f"- Exit reason: {loop_execution.get('exit_reason', '')}")
        lines.append(f"- Evidence: {loop_execution.get('evidence', '')}")
    commits_created = suggestion.get("commits_created") or report.get("batch_commits") or []
    if commits_created:
        lines.extend(["", "## Batch Commits", ""])
        for item in commits_created:
            lines.append(f"- `{item}`")
    if suggestion.get("workflow_issues"):
        lines.extend(["", "## Workflow Issues", ""])
        for item in suggestion["workflow_issues"]:
            lines.append(f"- {item}")
    git_after = suggestion.get("git_after") or {}
    if git_after.get("is_repo"):
        lines.extend(["", "## Git State", ""])
        lines.append(f"- Branch: `{git_after.get('branch') or 'detached'}`")
        lines.append(f"- Head: `{git_after.get('head') or 'unknown'}`")
        lines.append(f"- Dirty: `{'yes' if git_after.get('dirty') else 'no'}`")
    lines.extend(["", "## Phase Readiness", ""])
    lines.append(f"- Ready for certification: `{'yes' if readiness.get('ready_for_certification') else 'no'}`")
    lines.append(f"- Summary: {readiness.get('summary', 'No readiness summary.')}")
    lines.append(f"- Semantic issues: `{readiness.get('total_semantic_issues', 0)}`")
    lines.append(f"- Traceability issues: `{readiness.get('total_traceability_issues', 0)}`")
    if readiness.get("artifact_checks"):
        for check in readiness["artifact_checks"]:
            lines.append(f"- `{check['path']}` ready=`{'yes' if check.get('ready') else 'no'}` placeholders=`{check.get('placeholder_count', 0)}`")
            if check.get("missing_sections"):
                lines.append(f"  missing sections: {', '.join(check['missing_sections'])}")
            if check.get("thin_sections"):
                lines.append(f"  thin sections: {', '.join(check['thin_sections'])}")
            if check.get("semantic_issues"):
                lines.append(f"  semantic issues: {len(check['semantic_issues'])}")
                for issue in check["semantic_issues"]:
                    lines.append(f"  - {issue}")
            if check.get("semantic_metrics"):
                lines.append("  semantic metrics:")
                for key in sorted(check["semantic_metrics"]):
                    lines.append(f"  - {key}: {format_metric_value(check['semantic_metrics'][key])}")
    if readiness.get("traceability_checks"):
        lines.append("- Cross-phase traceability:")
        for check in readiness["traceability_checks"]:
            lines.append(
                f"  - `{check['name']}` ready=`{'yes' if check.get('ready') else 'no'}` "
                f"source=`{check.get('source_path')}` target=`{check.get('target_path')}`"
            )
            for issue in check.get("issues", []):
                lines.append(f"    - {issue}")
    if suggestion.get("response_excerpt"):
        lines.extend(["", "## Response Excerpt", "", suggestion["response_excerpt"]])
    if suggestion.get("stderr_excerpt"):
        lines.extend(["", "## Stderr Excerpt", "", suggestion["stderr_excerpt"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_metric_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def write_phase_readiness_md(path: Path, readiness: dict[str, Any]) -> None:
    lines = [
        "# Phase Readiness",
        "",
        f"- Phase: `{readiness['phase']}`",
        f"- Ready for certification: `{'yes' if readiness.get('ready_for_certification') else 'no'}`",
        f"- Summary: {readiness.get('summary', '')}",
        f"- Missing sections: `{readiness.get('total_missing_sections', 0)}`",
        f"- Thin sections: `{readiness.get('total_thin_sections', 0)}`",
        f"- Placeholder lines: `{readiness.get('total_placeholders', 0)}`",
        f"- Semantic issues: `{readiness.get('total_semantic_issues', 0)}`",
        f"- Traceability issues: `{readiness.get('total_traceability_issues', 0)}`",
        "",
        "## Artifact Checks",
        "",
    ]
    for check in readiness.get("artifact_checks", []):
        lines.append(f"- `{check['path']}` ready=`{'yes' if check.get('ready') else 'no'}` placeholders=`{check.get('placeholder_count', 0)}`")
        if check.get("missing_sections"):
            lines.append(f"  missing sections: {', '.join(check['missing_sections'])}")
        if check.get("thin_sections"):
            lines.append(f"  thin sections: {', '.join(check['thin_sections'])}")
        if check.get("semantic_issues"):
            lines.append(f"  semantic issues: {len(check['semantic_issues'])}")
            for issue in check["semantic_issues"]:
                lines.append(f"  - {issue}")
        if check.get("semantic_metrics"):
            lines.append("  semantic metrics:")
            for key in sorted(check["semantic_metrics"]):
                lines.append(f"  - {key}: {format_metric_value(check['semantic_metrics'][key])}")
    if readiness.get("traceability_checks"):
        lines.extend(["", "## Cross-Phase Traceability", ""])
        for check in readiness["traceability_checks"]:
            lines.append(
                f"- `{check['name']}` ready=`{'yes' if check.get('ready') else 'no'}` "
                f"source=`{check.get('source_path')}` target=`{check.get('target_path')}`"
            )
            for issue in check.get("issues", []):
                lines.append(f"  - {issue}")
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
    readiness_path: Path,
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
        f"- Phase readiness: `{display_path(readiness_path)}`",
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
    phase_readiness_path: Path,
    command_argv: list[str] | None,
    git_before: dict[str, Any],
    git_after: dict[str, Any],
    created_commits: list[str],
    loop_contract: dict[str, Any] | None = None,
    loop_plugin_metadata: dict[str, str] | None = None,
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
        f"- Phase readiness: `{display_path(phase_readiness_path)}`",
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

    if git_after.get("is_repo"):
        lines.extend(
            [
                "",
                "## Git",
                "",
                f"- Branch before: `{git_before.get('branch') or 'detached'}`",
                f"- Head before: `{git_before.get('head') or 'unknown'}`",
                f"- Branch after: `{git_after.get('branch') or 'detached'}`",
                f"- Head after: `{git_after.get('head') or 'unknown'}`",
                f"- Dirty after: `{'yes' if git_after.get('dirty') else 'no'}`",
            ]
        )
        if created_commits:
            lines.append("- Commits created:")
            for item in created_commits:
                lines.append(f"  - `{item}`")

    if loop_contract:
        lines.extend(
            [
                "",
                "## Ralph Loop",
                "",
                f"- Session id: `{loop_contract['session_id']}`",
                f"- Plugin dir: `{display_path(Path(loop_contract['plugin_dir']))}`",
                f"- State file: `{display_path(Path(loop_contract['state_file']))}`",
                f"- Prompt file: `{display_path(Path(loop_contract['prompt_file']))}`",
                f"- Audit summary: `{display_path(Path(loop_contract['audit_summary_file']))}`",
                f"- Audit events: `{display_path(Path(loop_contract['audit_events_file']))}`",
                f"- Completion promise: `{loop_contract['completion_promise']}`",
                f"- Max iterations: `{loop_contract['max_iterations']}`",
            ]
        )
        if loop_plugin_metadata:
            lines.append(f"- Claude plugin id: `{loop_plugin_metadata.get('id', '')}`")
            if loop_plugin_metadata.get("version"):
                lines.append(f"- Claude plugin version: `{loop_plugin_metadata.get('version', '')}`")

    lines.extend(["", "## Next Action", ""])
    if dry_run:
        lines.append("- Review the execution packet, then rerun without `--dry-run` when you are ready.")
    elif status == "unsupported":
        lines.append(
            f"- Review `result-suggestion.md`, then use `{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id <id> --packet <packet-dir>` to record the manual-follow-up result."
        )
    elif status == "failed":
        lines.append(
            f"- Review `result-suggestion.md`, then use `{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id <id> --packet <packet-dir>` to record the blocked result before rerunning if needed."
        )
    else:
        lines.append(
            f"- Review `result-suggestion.md`, then apply it with `{supernb_cli_prefix(ROOT_DIR)} apply-execution --initiative-id <id> --packet <packet-dir>`."
        )

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
    global DISPLAY_ROOTS
    DISPLAY_ROOTS = [project_root(spec), ROOT_DIR]
    debug_log(
        spec,
        "start",
        {
            "spec_path": str(spec_path),
            "phase_arg": args.phase,
            "harness_arg": args.harness,
            "project_dir_arg": args.project_dir or "",
            "prompt_arg": args.prompt_file or "",
            "dry_run": args.dry_run,
        },
    )
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    try:
        _, payload = resolve_run_payload(spec)
        phase = resolve_phase(args, payload)
        prompt_source = resolve_prompt_path(args, payload, spec)
        project_dir = resolve_project_dir(args, spec)
        harness = resolve_harness(args, spec, project_dir)
    except (FileNotFoundError, ValueError) as exc:
        debug_log(
            spec,
            "resolve-error",
            {
                "error": str(exc),
            },
        )
        print(str(exc), file=sys.stderr)
        return 1

    if not prompt_source.is_file():
        debug_log(
            spec,
            "prompt-missing",
            {
                "prompt_source": str(prompt_source),
                "phase": phase,
                "harness": harness,
            },
        )
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
    prompt_with_report_text = prompt_text + execution_policy(spec, phase, project_dir) + response_contract(phase)
    direct_loop_contract: dict[str, Any] | None = None
    if harness == "claude-code" and phase in LOOP_REQUIRED_PHASES:
        direct_loop_contract = build_direct_loop_contract(initiative_id, phase, packet_dir, project_dir)
        prompt_with_report_text += direct_loop_policy(direct_loop_contract)
        Path(direct_loop_contract["prompt_file"]).write_text(prompt_with_report_text, encoding="utf-8")
    prompt_with_report_path.write_text(prompt_with_report_text, encoding="utf-8")
    response_path = packet_dir / "response.md"
    stdout_path = packet_dir / "stdout.log"
    stderr_path = packet_dir / "stderr.log"
    summary_path = packet_dir / "summary.md"
    request_path = packet_dir / "request.json"
    result_suggestion_json = packet_dir / "result-suggestion.json"
    result_suggestion_md = packet_dir / "result-suggestion.md"
    phase_readiness_json = packet_dir / "phase-readiness.json"
    phase_readiness_md = packet_dir / "phase-readiness.md"

    status = "prepared"
    exit_code: int | None = None
    command_argv: list[str] | None = None
    error_message = ""
    git_before = git_state(project_dir)
    git_after = git_before
    created_commits: list[str] = []
    loop_plugin_metadata: dict[str, str] = {}
    direct_loop_audit_summary: dict[str, Any] | None = None

    if harness not in DIRECT_EXECUTION_HARNESSES:
        status = "unsupported"
        error_message = f"Direct execute-next support is not available for harness: {harness}"
    else:
        binary = "codex" if harness == "codex" else "claude"
        if not shutil.which(binary):
            status = "unsupported"
            error_message = f"{binary} CLI is not installed or not on PATH."
        else:
            command_argv = build_execution_command(harness, project_dir, response_path, args.cli_arg, direct_loop_contract)

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
            "git_before": git_before,
            "ralph_loop": serialize_loop_contract(direct_loop_contract),
            "ralph_loop_plugin": loop_plugin_metadata,
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
        manual_note = "- Use the prepared prompt manually in the target harness.\n"
        if harness == "opencode":
            manual_note = (
                "- Open the prepared `prompt-with-report.md` in your OpenCode project session.\n"
                f"- Run that prompt manually in OpenCode, then return to `{supernb_cli_prefix(ROOT_DIR)} apply-execution` with this packet.\n"
            )
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(error_message + "\n", encoding="utf-8")
        response_path.write_text(
            "# Direct Execution Unavailable\n\n"
            f"- {error_message}\n"
            f"{manual_note}",
            encoding="utf-8",
        )
    else:
        if direct_loop_contract:
            try:
                loop_plugin_metadata = start_direct_claude_loop(project_dir, direct_loop_contract)
                direct_loop_audit_summary = wait_for_loop_state_observed(direct_loop_contract)
                if not direct_loop_audit_summary or not direct_loop_audit_summary.get("state_observed"):
                    raise RuntimeError(
                        "Ralph Loop audit watcher did not confirm the state file before Claude Code execution started. "
                        "The direct Claude run was not launched because the loop contract could not be externally observed."
                    )
            except (FileNotFoundError, RuntimeError) as exc:
                status = "failed"
                exit_code = 1
                error_message = str(exc)
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text(error_message + "\n", encoding="utf-8")
                response_path.write_text(
                    "# Ralph Loop Setup Failed\n\n"
                    f"- {error_message}\n"
                    "- Fix the Claude Code loop environment and rerun this packet.\n",
                    encoding="utf-8",
                )

        if status != "failed":
            run_env = None
            if direct_loop_contract:
                run_env = dict(os.environ)
                run_env["CLAUDE_CODE_SESSION_ID"] = direct_loop_contract["session_id"]
            proc = subprocess.run(
                command_argv,
                input=prompt_with_report_text,
                text=True,
                capture_output=True,
                cwd=str(project_dir),
                env=run_env,
            )
            exit_code = proc.returncode
            stdout_path.write_text(proc.stdout, encoding="utf-8")
            stderr_path.write_text(proc.stderr, encoding="utf-8")

            if harness == "claude-code":
                response_path.write_text(proc.stdout, encoding="utf-8")
            elif not response_path.exists():
                response_path.write_text("", encoding="utf-8")

            if direct_loop_contract:
                direct_loop_audit_summary = wait_for_loop_audit_summary(direct_loop_contract)

            status = "succeeded" if proc.returncode == 0 else "failed"

    git_after = git_state(project_dir)
    created_commits = commits_created(project_dir, git_before, git_after)
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
            "git_before": git_before,
            "git_after": git_after,
            "commits_created": created_commits,
            "ralph_loop": serialize_loop_contract(direct_loop_contract),
            "ralph_loop_plugin": loop_plugin_metadata,
            "ralph_loop_audit_summary": direct_loop_audit_summary or {},
        },
    )

    response_text = response_path.read_text(encoding="utf-8") if response_path.exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
    phase_readiness = build_phase_readiness(spec, phase)
    write_json(phase_readiness_json, phase_readiness)
    write_phase_readiness_md(phase_readiness_md, phase_readiness)
    suggestion = build_result_suggestion(
        phase,
        harness,
        status,
        args.dry_run,
        exit_code,
        response_text,
        stderr_text,
        packet_dir,
        project_dir,
        phase_readiness,
        git_before,
        git_after,
        created_commits,
    )
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
        phase_readiness_md,
        command_argv,
        git_before,
        git_after,
        created_commits,
        direct_loop_contract,
        loop_plugin_metadata,
    )
    append_run_log(run_log_path, phase, harness, args.dry_run, status, exit_code, packet_dir, prompt_source, response_path, result_suggestion_md, phase_readiness_md)
    debug_log(
        spec,
        "complete",
        {
            "initiative_id": initiative_id,
            "phase": phase,
            "harness": harness,
            "dry_run": args.dry_run,
            "status": status,
            "exit_code": exit_code,
            "packet_dir": display_path(packet_dir),
            "prompt_source": display_path(prompt_source),
            "result_suggestion": display_path(result_suggestion_md),
            "phase_readiness_ready": bool(phase_readiness.get("ready_for_certification")),
            "phase_readiness_missing_sections": int(phase_readiness.get("total_missing_sections", 0)),
            "phase_readiness_thin_sections": int(phase_readiness.get("total_thin_sections", 0)),
            "phase_readiness_semantic_issues": int(phase_readiness.get("total_semantic_issues", 0)),
            "workflow_issues": suggestion.get("workflow_issues", []),
            "suggested_result_status": suggestion.get("suggested_result_status", ""),
            "ralph_loop": serialize_loop_contract(direct_loop_contract),
            "ralph_loop_plugin": loop_plugin_metadata,
            "ralph_loop_audit_final_status": (direct_loop_audit_summary or {}).get("final_status", ""),
        },
    )

    print(f"Initiative: {initiative_id}")
    print(f"Phase: {phase}")
    print(f"Harness: {harness}")
    print(f"Project dir: {project_dir}")
    print(f"Execution packet: {packet_dir}")
    print(f"Summary: {summary_path}")
    print(f"Response: {response_path}")
    print(f"Result suggestion: {result_suggestion_md}")
    print(f"Phase readiness: {phase_readiness_md}")
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
