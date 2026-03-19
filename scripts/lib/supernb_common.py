from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PHASES = ["research", "prd", "design", "planning", "delivery", "release"]


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
