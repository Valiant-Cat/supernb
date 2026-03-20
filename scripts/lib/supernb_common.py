from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASES = ["research", "prd", "design", "planning", "delivery", "release"]
DEBUG_LOG_ENV_VAR = "SUPERNB_DEBUG_LOG"
RALPH_LOOP_PLUGIN_ID = "superpowers@frad-dotclaude"
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
        if plugin_id.startswith("superpowers@") and metadata.get("status") == "enabled"
    )


def assert_ralph_loop_environment(project_dir: Path) -> dict[str, str]:
    inventory = claude_plugin_inventory(project_dir)
    enabled = sorted(
        plugin_id
        for plugin_id, metadata in inventory.items()
        if plugin_id.startswith("superpowers@") and metadata.get("status") == "enabled"
    )
    if RALPH_LOOP_PLUGIN_ID not in enabled:
        enabled_text = ", ".join(enabled) if enabled else "none"
        raise RuntimeError(
            "Ralph Loop requires an enabled Claude Code loop environment. "
            f"Expected `{RALPH_LOOP_PLUGIN_ID}` but found enabled superpowers plugins: {enabled_text}. "
            "Install or switch to the FradSer/dotclaude superpowers plugin before starting planning or delivery loop execution."
        )
    if len(enabled) > 1:
        raise RuntimeError(
            "Ralph Loop environment is ambiguous because multiple `superpowers@...` plugins are enabled in Claude Code: "
            + ", ".join(enabled)
            + ". Use a single loop-enabled superpowers plugin environment for planning or delivery execution."
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
