from __future__ import annotations

import json
import hashlib
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASES = ["research", "prd", "design", "planning", "delivery", "release"]
DEBUG_LOG_ENV_VAR = "SUPERNB_DEBUG_LOG"
RALPH_LOOP_PLUGIN_ID = "supernb-loop@supernb"
LOOP_REQUIRED_PHASES = {"planning", "delivery"}
SNAPSHOT_IGNORED_METADATA_FIELDS = {
    "Status",
    "Approval status",
    "Ready for execution",
    "Delivery status",
    "Release decision",
    "Approved by",
    "Approved on",
}


def try_load_pyyaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    return yaml.safe_load(text)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def markdown_field_from_text(text: str, label: str) -> str:
    pattern = rf"^- {re.escape(label)}:\s*(.*)$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def markdown_field(path: Path, label: str) -> str:
    if not path.is_file():
        return ""
    return markdown_field_from_text(path.read_text(encoding="utf-8"), label)


def display_path(path: Path, roots: list[Path]) -> str:
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def project_root(spec: dict[str, Any], root_dir: Path) -> Path:
    project_dir = nested_get(spec, "delivery", "project_dir")
    if project_dir:
        return Path(project_dir).expanduser().resolve()
    return root_dir


def artifact_path(spec: dict[str, Any], key: str, root_dir: Path, default: Path | None = None) -> Path:
    value = nested_get(spec, "artifacts", key)
    if value:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (project_root(spec, root_dir) / path).resolve()
    if default is not None:
        return default.resolve()
    raise KeyError(f"Missing artifact path: {key}")


def resolve_existing_path(raw_path: str, base_dirs: list[Path] | None = None) -> Path | None:
    value = str(raw_path).strip()
    if not value:
        return None
    fingerprint_match = re.match(r"^(?P<path>.+?) \(\d+ lines, sha256:[0-9a-f]{64}\)$", value)
    if fingerprint_match:
        value = fingerprint_match.group("path").strip()

    candidate = Path(value).expanduser()
    search_roots = base_dirs or []
    candidates: list[Path] = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        for root in search_roots:
            candidates.append(root / candidate)
        candidates.append(Path.cwd() / candidate)

    seen: set[Path] = set()
    for item in candidates:
        try:
            resolved = item.resolve()
        except FileNotFoundError:
            resolved = item.expanduser().absolute()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists():
            return resolved
    return None


def resolve_spec_path(args: Any, root_dir: Path) -> Path:
    spec_arg = getattr(args, "spec", None)
    if spec_arg:
        return Path(spec_arg).expanduser().resolve()

    initiative_id = getattr(args, "initiative_id", None)
    if not initiative_id:
        raise ValueError("Pass --initiative-id or --spec.")

    locator = root_dir / "artifacts" / "initiative-locations" / f"{initiative_id}.txt"
    if locator.is_file():
        target = Path(locator.read_text(encoding="utf-8").strip()).expanduser()
        if target.is_file():
            return target.resolve()

    for base in [Path.cwd(), *Path.cwd().parents]:
        for candidate in [
            base / ".supernb" / "initiatives" / initiative_id / "initiative.yaml",
            base / "artifacts" / "initiatives" / initiative_id / "initiative.yaml",
        ]:
            if candidate.is_file():
                return candidate.resolve()

    legacy = root_dir / "artifacts" / "initiatives" / initiative_id / "initiative.yaml"
    if legacy.is_file():
        return legacy.resolve()
    return legacy


def initiative_dir(spec: dict[str, Any], root_dir: Path) -> Path:
    run_status = artifact_path(
        spec,
        "run_status_md",
        root_dir,
        default=project_root(spec, root_dir) / ".supernb" / "initiatives" / f"{nested_get(spec, 'initiative', 'id')}" / "run-status.md",
    )
    return run_status.parent.resolve()


def parse_bool_flag(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled"}:
        return False
    return None


def debug_log_toggle_path(project_dir: Path) -> Path:
    return project_dir / ".supernb" / "debug-logging.enabled"


def supernb_cli_path(root_dir: Path) -> Path:
    return (root_dir / "scripts" / "supernb").resolve()


def supernb_cli_prefix(root_dir: Path) -> str:
    return shlex.quote(str(supernb_cli_path(root_dir)))


def debug_log_env_override() -> bool | None:
    return parse_bool_flag(os.getenv(DEBUG_LOG_ENV_VAR))


def debug_log_enabled(project_dir: Path) -> bool:
    env_override = debug_log_env_override()
    if env_override is not None:
        return env_override
    return debug_log_toggle_path(project_dir).is_file()


def debug_log_dir(spec: dict[str, Any], root_dir: Path) -> Path:
    return initiative_dir(spec, root_dir) / "debug-logs"


def append_debug_log(
    spec: dict[str, Any],
    root_dir: Path,
    component: str,
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    force: bool = False,
) -> Path | None:
    project_dir = project_root(spec, root_dir)
    if not force and not debug_log_enabled(project_dir):
        return None

    try:
        log_dir = debug_log_dir(spec, root_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{datetime.now().strftime('%Y%m%d')}.ndjson"
        record = {
            "timestamp": utc_now(),
            "component": component,
            "event": event,
            "initiative_id": nested_get(spec, "initiative", "id"),
            "project_dir": str(project_dir),
            "cwd": str(Path.cwd()),
            "pid": os.getpid(),
            "payload": payload or {},
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return log_path
    except OSError:
        return None


def parse_claude_plugin_list(output: str) -> dict[str, dict[str, str]]:
    plugins: dict[str, dict[str, str]] = {}
    current_id = ""

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        plugin_match = re.match(r"^\s*[❯>*-]?\s*(superpowers@[^\s]+|[A-Za-z0-9_.-]+@[^\s]+)\s*$", line)
        if plugin_match:
            current_id = plugin_match.group(1).strip()
            plugins[current_id] = {"id": current_id}
            continue
        if not current_id:
            continue
        field_match = re.match(r"^\s*(Version|Scope|Status):\s*(.+?)\s*$", line)
        if not field_match:
            continue
        key = field_match.group(1).lower()
        value = field_match.group(2).strip()
        if key == "status":
            if "enabled" in value:
                plugins[current_id]["status"] = "enabled"
            elif "disabled" in value:
                plugins[current_id]["status"] = "disabled"
            else:
                plugins[current_id]["status"] = value
        else:
            plugins[current_id][key] = value
    return plugins


def claude_plugin_inventory(project_dir: Path) -> dict[str, dict[str, str]]:
    try:
        proc = subprocess.run(
            ["claude", "plugin", "list"],
            cwd=project_dir,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("`claude` CLI is not installed or not on PATH, so Ralph Loop cannot verify the Claude plugin environment.") from exc
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "unknown claude plugin list error"
        raise RuntimeError(f"`claude plugin list` failed in {project_dir}: {message}")
    return parse_claude_plugin_list(proc.stdout)


def enabled_superpowers_plugins(project_dir: Path) -> list[str]:
    inventory = claude_plugin_inventory(project_dir)
    return sorted(
        plugin_id
        for plugin_id, metadata in inventory.items()
        if metadata.get("status") == "enabled"
    )


def assert_ralph_loop_environment(project_dir: Path) -> dict[str, str]:
    inventory = claude_plugin_inventory(project_dir)
    enabled = sorted(
        plugin_id
        for plugin_id, metadata in inventory.items()
        if metadata.get("status") == "enabled"
    )
    if RALPH_LOOP_PLUGIN_ID not in enabled:
        enabled_text = ", ".join(enabled) if enabled else "none"
        raise RuntimeError(
            "Ralph Loop requires an enabled Claude Code loop environment. "
            f"Expected `{RALPH_LOOP_PLUGIN_ID}` but found enabled Claude Code plugins: {enabled_text}. "
            "Install or enable the managed supernb loop plugin before starting planning or delivery loop execution."
        )
    return inventory[RALPH_LOOP_PLUGIN_ID]


def certification_state_path(spec: dict[str, Any], root_dir: Path) -> Path:
    return artifact_path(
        spec,
        "certification_state_json",
        root_dir,
        default=initiative_dir(spec, root_dir) / "certification-state.json",
    )


def load_certification_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"phases": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"phases": {}}
    if not isinstance(payload, dict):
        return {"phases": {}}
    phases = payload.get("phases")
    if not isinstance(phases, dict):
        payload["phases"] = {}
    return payload


def certification_passed(entry: dict[str, Any] | None, expected_status: str = "") -> bool:
    if not isinstance(entry, dict):
        return False
    if not bool(entry.get("passed")):
        return False
    if expected_status:
        return str(entry.get("recommended_gate_status", "")).strip().lower() == expected_status.strip().lower()
    return True


def certification_snapshot_matches(entry: dict[str, Any] | None, current_snapshot: list[dict[str, Any]] | None = None) -> bool:
    if current_snapshot is None:
        return True
    if not isinstance(entry, dict):
        return False
    snapshot = entry.get("artifact_snapshot")
    if not isinstance(snapshot, list):
        return False
    return snapshot == current_snapshot


def load_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def normalized_choice(value: str) -> str:
    return str(value).strip().lower().strip("`")


def run_status_indicates_completed_cycle(run_status_json: Path) -> bool:
    payload = load_json_file(run_status_json)
    if not payload:
        return False
    phases = payload.get("phases")
    if not isinstance(phases, dict):
        return False
    delivery_status = normalized_choice(nested_get(phases.get("delivery", {}), "status"))
    release_status = normalized_choice(nested_get(phases.get("release", {}), "status"))
    selected_phase = normalized_choice(str(payload.get("selected_phase", "")))
    return (
        delivery_status == "complete" and release_status == "complete"
    ) or (
        selected_phase == "release" and release_status == "complete"
    )


def reassessment_indicates_next_development_cycle(reassessment_path: Path) -> bool:
    if not reassessment_path.is_file():
        return False
    text = reassessment_path.read_text(encoding="utf-8")
    status = normalized_choice(markdown_field_from_text(text, "Status"))
    current_phase = normalized_choice(markdown_field_from_text(text, "Current selected phase"))
    earliest_phase = normalized_choice(markdown_field_from_text(text, "Earliest affected phase to reopen"))
    can_continue = normalized_choice(markdown_field_from_text(text, "Can the current selected phase continue without reopening upstream work"))
    if status != "completed":
        return False
    if earliest_phase not in {"none", "n/a", "not-applicable", "not applicable"}:
        return False
    if can_continue != "yes":
        return False
    lowered = text.lower()
    cycle_signals = (
        "ready for next development cycle",
        "future batch",
        "future batches",
        "all phases complete and certified",
        "all phases complete.",
    )
    return current_phase == "release" and any(signal in lowered for signal in cycle_signals)


def prompt_first_reassessment_path(spec: dict[str, Any], root_dir: Path) -> Path:
    return initiative_dir(spec, root_dir) / "initiative-reassessment.md"


def prompt_first_blocker_path(spec: dict[str, Any], root_dir: Path, phase: str) -> Path:
    return initiative_dir(spec, root_dir) / f"prompt-first-blocker-{phase}.json"


def phase_has_recorded_activity(spec: dict[str, Any], root_dir: Path, phase: str) -> bool:
    initiative_root = initiative_dir(spec, root_dir)
    executions_dir = artifact_path(spec, "executions_dir", root_dir, default=initiative_root / "executions")
    phase_results_dir = artifact_path(spec, "phase_results_dir", root_dir, default=initiative_root / "phase-results")

    if prompt_first_blocker_path(spec, root_dir, phase).is_file():
        return True
    if executions_dir.exists() and any(executions_dir.glob(f"*-{phase}-*")):
        return True
    if phase_results_dir.exists() and any(phase_results_dir.glob(f"*-{phase}-*.md")):
        return True
    return False


def git_head(project_dir: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def prompt_first_progress_signature(spec: dict[str, Any], root_dir: Path, phase: str) -> dict[str, Any]:
    project_dir = project_root(spec, root_dir)
    return {
        "phase": phase,
        "git_head": git_head(project_dir),
        "phase_artifact_snapshot": phase_artifact_snapshot(spec, phase, root_dir, [project_dir, root_dir]),
    }


def load_prompt_first_blocker(spec: dict[str, Any], root_dir: Path, phase: str) -> dict[str, Any] | None:
    path = prompt_first_blocker_path(spec, root_dir, phase)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def write_prompt_first_blocker(
    spec: dict[str, Any],
    root_dir: Path,
    phase: str,
    *,
    packet_dir: Path | None = None,
    reason: str = "",
    detail: str = "",
) -> Path:
    path = prompt_first_blocker_path(spec, root_dir, phase)
    payload = {
        "phase": phase,
        "recorded_at": utc_now(),
        "packet_dir": str(packet_dir.resolve()) if packet_dir else "",
        "reason": reason,
        "detail": detail,
        "progress_signature": prompt_first_progress_signature(spec, root_dir, phase),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def clear_prompt_first_blocker(spec: dict[str, Any], root_dir: Path, phase: str) -> None:
    path = prompt_first_blocker_path(spec, root_dir, phase)
    path.unlink(missing_ok=True)


def prompt_first_retry_blocker(
    spec: dict[str, Any],
    root_dir: Path,
    phase: str,
    *,
    source_packet: Path | None = None,
) -> str | None:
    payload = load_prompt_first_blocker(spec, root_dir, phase)
    if not payload:
        return None
    path = prompt_first_blocker_path(spec, root_dir, phase)
    current_signature = prompt_first_progress_signature(spec, root_dir, phase)
    if payload.get("progress_signature") != current_signature:
        clear_prompt_first_blocker(spec, root_dir, phase)
        return None
    packet_dir = str(payload.get("packet_dir", "")).strip()
    if source_packet is not None:
        blocked_packet = Path(packet_dir).expanduser().resolve() if packet_dir else None
        candidate_packet = source_packet.expanduser().resolve()
        if blocked_packet is None or blocked_packet != candidate_packet:
            clear_prompt_first_blocker(spec, root_dir, phase)
            return None
    return (
        f"Prompt-first {phase} closeout already failed without any new git or artifact progress. "
        "Do not rerun closeout/import on the same unchanged state. Resolve the existing blockers first, "
        "or make real code/artifact progress before retrying. "
        f"Blocker record: {path}."
        + (f" Last failed packet: {packet_dir}." if packet_dir else "")
    )


def prompt_first_reassessment_blocker(spec: dict[str, Any], root_dir: Path, spec_path: Path, phase: str) -> str | None:
    reassessment_path = prompt_first_reassessment_path(spec, root_dir)
    if not reassessment_path.is_file():
        return (
            "Prompt-first execution requires a completed initiative-wide reassessment, but the managed reassessment file is missing: "
            f"{reassessment_path}. Run `{supernb_cli_prefix(root_dir)} prompt-sync --spec {spec_path}` or "
            f"`{supernb_cli_prefix(root_dir)} prompt-bootstrap --spec {spec_path}` before continuing this prompt-first batch."
        )

    text = reassessment_path.read_text(encoding="utf-8")
    status = normalized_choice(markdown_field_from_text(text, "Status"))
    earliest_phase = normalized_choice(markdown_field_from_text(text, "Earliest affected phase to reopen"))
    can_continue = normalized_choice(markdown_field_from_text(text, "Can the current selected phase continue without reopening upstream work"))

    if not status or status == "pending":
        return (
            f"Prompt-first execution requires a completed initiative-wide reassessment before {phase} can finish. "
            f"Update `{reassessment_path}` and change `- Status:` from `pending` to a completed state first."
        )
    if not earliest_phase:
        return (
            f"Prompt-first execution requires `{reassessment_path}` to record `Earliest affected phase to reopen` "
            "before the batch can continue."
        )
    if can_continue not in {"yes", "no"}:
        return (
            f"Prompt-first execution requires `{reassessment_path}` to answer whether the current phase can continue without reopening upstream work."
        )
    if can_continue == "no":
        return (
            f"Initiative-wide reassessment says the current `{phase}` batch cannot continue cleanly until an earlier phase is reopened. "
            f"Next step: run `{supernb_cli_prefix(root_dir)} prompt-bootstrap --spec {spec_path} --phase {earliest_phase}` "
            "after updating the upstream artifacts."
        )
    if reassessment_indicates_next_development_cycle(reassessment_path):
        project_dir = project_root(spec, root_dir)
        return (
            "Initiative-wide reassessment says the current initiative has already completed its release-ready cycle and the request belongs in the next "
            "development cycle. Do not continue more work into the current initiative. "
            f"Next step: run `{supernb_cli_prefix(root_dir)} prompt-bootstrap --project-dir {project_dir}` to start a new follow-on initiative."
        )
    return None


def phase_targets(spec: dict[str, Any], phase: str, root_dir: Path) -> list[Path]:
    if phase == "research":
        root = artifact_path(spec, "research_dir", root_dir)
        return [
            root / "01-competitor-landscape.md",
            root / "02-review-insights.md",
            root / "03-feature-opportunities.md",
        ]
    if phase == "prd":
        return [artifact_path(spec, "prd_dir", root_dir) / "product-requirements.md"]
    if phase == "design":
        root = artifact_path(spec, "design_dir", root_dir)
        return [root / "ui-ux-spec.md", root / "i18n-strategy.md"]
    if phase in {"planning", "delivery"}:
        return [artifact_path(spec, "plan_dir", root_dir) / "implementation-plan.md"]
    return [artifact_path(spec, "release_dir", root_dir) / "release-readiness.md"]


def phase_snapshot_paths(spec: dict[str, Any], phase: str, root_dir: Path) -> list[Path]:
    paths = phase_targets(spec, phase, root_dir)
    if phase == "delivery":
        paths = [*paths, artifact_path(spec, "release_dir", root_dir) / "release-readiness.md"]
    return paths


def normalized_snapshot_bytes(path: Path) -> bytes:
    if path.suffix.lower() != ".md":
        return path.read_bytes()

    normalized_lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^-\s+([^:]+):\s*(.*)$", raw_line.strip())
        if match and match.group(1).strip() in SNAPSHOT_IGNORED_METADATA_FIELDS:
            normalized_lines.append(f"- {match.group(1).strip()}:")
            continue
        normalized_lines.append(raw_line.rstrip())
    return ("\n".join(normalized_lines) + "\n").encode("utf-8")


def file_fingerprint(path: Path, roots: list[Path]) -> dict[str, Any]:
    if not path.exists():
        return {"path": display_path(path, roots), "exists": False}
    normalized_bytes = normalized_snapshot_bytes(path)
    digest = hashlib.sha256(normalized_bytes).hexdigest()
    return {
        "path": display_path(path, roots),
        "exists": True,
        "normalized_size": len(normalized_bytes),
        "sha256": digest,
    }


def phase_artifact_snapshot(spec: dict[str, Any], phase: str, root_dir: Path, display_roots: list[Path] | None = None) -> list[dict[str, Any]]:
    roots = display_roots or [project_root(spec, root_dir), root_dir]
    return [file_fingerprint(path, roots) for path in phase_snapshot_paths(spec, phase, root_dir)]
