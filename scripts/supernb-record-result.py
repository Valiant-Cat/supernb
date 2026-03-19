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


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return ROOT_DIR / nested_get(spec, "artifacts", key)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    if args.spec:
        return Path(args.spec).expanduser().resolve()
    if args.initiative_id:
        return ROOT_DIR / "artifacts" / "initiatives" / args.initiative_id / "initiative.yaml"
    raise ValueError("Pass --initiative-id or --spec.")


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
    initiative_id = nested_get(spec, "initiative", "id") or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    phase = args.phase or current_phase_from_run_status(spec)
    results_dir = artifact_path(spec, "phase_results_dir")
    run_log_path = artifact_path(spec, "run_log_md")
    results_dir.mkdir(parents=True, exist_ok=True)

    notes = ""
    if args.notes_file:
        notes = Path(args.notes_file).expanduser().read_text(encoding="utf-8").strip()

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
    if args.artifact_path:
        for artifact in args.artifact_path:
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
            "- Update the relevant artifact status fields if this execution should advance the gate.",
            f"- Re-run `./scripts/supernb run --initiative-id {initiative_id}` after artifact status changes.",
        ]
    )
    result_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    append_to_run_log(run_log_path, phase, args.status, args.summary, result_path, args.artifact_path)

    print(f"Recorded phase result: {result_path}")
    if not args.no_rerun:
        subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--initiative-id", initiative_id], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
