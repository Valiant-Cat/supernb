#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DISPLAY_ROOTS = [ROOT_DIR]
PHASES = ["research", "prd", "design", "planning", "delivery", "release"]


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
    for root in DISPLAY_ROOTS:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return str(path)


def project_root(spec: dict[str, Any]) -> Path:
    project_dir = nested_get(spec, "delivery", "project_dir")
    if project_dir:
        return Path(project_dir).expanduser().resolve()
    return ROOT_DIR


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    value = nested_get(spec, "artifacts", key)
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (project_root(spec) / path).resolve()


def resolve_spec_path(args: argparse.Namespace) -> Path:
    if args.spec:
        return Path(args.spec).expanduser().resolve()
    if args.initiative_id:
        locator = ROOT_DIR / "artifacts" / "initiative-locations" / f"{args.initiative_id}.txt"
        if locator.is_file():
            target = Path(locator.read_text(encoding="utf-8").strip()).expanduser()
            if target.is_file():
                return target.resolve()
        for base in [Path.cwd(), *Path.cwd().parents]:
            for candidate in [
                base / ".supernb" / "initiatives" / args.initiative_id / "initiative.yaml",
                base / "artifacts" / "initiatives" / args.initiative_id / "initiative.yaml",
            ]:
                if candidate.is_file():
                    return candidate.resolve()
        return ROOT_DIR / "artifacts" / "initiatives" / args.initiative_id / "initiative.yaml"
    raise ValueError("Pass --initiative-id or --spec.")


def replace_field(path: Path, field: str, value: str) -> None:
    pattern = re.compile(rf"^(- {re.escape(field)}:).*$", re.MULTILINE)
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(rf"\1 {value}", text, count=1)
    if count == 0:
        raise ValueError(f"Field '{field}' not found in {path}")
    path.write_text(updated, encoding="utf-8")


def phase_targets(spec: dict[str, Any], phase: str) -> list[Path]:
    if phase == "research":
        root = artifact_path(spec, "research_dir")
        return [
            root / "01-competitor-landscape.md",
            root / "02-review-insights.md",
            root / "03-feature-opportunities.md",
        ]
    if phase == "prd":
        return [artifact_path(spec, "prd_dir") / "product-requirements.md"]
    if phase == "design":
        root = artifact_path(spec, "design_dir")
        return [root / "ui-ux-spec.md", root / "i18n-strategy.md"]
    if phase in {"planning", "delivery"}:
        return [artifact_path(spec, "plan_dir") / "implementation-plan.md"]
    return [artifact_path(spec, "release_dir") / "release-readiness.md"]


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

    print(f"Applied phase status: {args.phase} -> {args.status}")
    print(f"Gate update record: {result_path}")

    if not args.no_rerun:
        subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--initiative-id", initiative_id], check=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
