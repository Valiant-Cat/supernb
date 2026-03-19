#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a saved execution packet into result recording and optional certification.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--packet", required=True, help="Path to an execution packet directory")
    parser.add_argument("--status", default="auto", help="Result status override. Defaults to the packet suggestion.")
    parser.add_argument("--summary", help="Result summary override. Defaults to the packet suggestion.")
    parser.add_argument("--certify", action="store_true", help="Run certify-phase after recording the result")
    parser.add_argument("--apply-certification", action="store_true", help="When certification passes, also apply the phase gate")
    parser.add_argument("--actor", default="supernb", help="Actor name used for certification apply")
    parser.add_argument("--date", help="Approval date forwarded to certify-phase --apply")
    parser.add_argument("--no-rerun", action="store_true", help="Do not rerun supernb after recording or certifying")
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
    return str(current).strip()


def resolve_spec_path(args: argparse.Namespace) -> Path:
    if args.spec:
        return Path(args.spec).expanduser().resolve()
    if args.initiative_id:
        return ROOT_DIR / "artifacts" / "initiatives" / args.initiative_id / "initiative.yaml"
    raise ValueError("Pass --initiative-id or --spec.")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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

    packet_dir = Path(args.packet).expanduser().resolve()
    if not packet_dir.is_dir():
        print(f"Execution packet not found: {packet_dir}", file=sys.stderr)
        return 1

    request_path = packet_dir / "request.json"
    suggestion_path = packet_dir / "result-suggestion.json"
    if not request_path.is_file():
        print(f"Missing request metadata in packet: {request_path}", file=sys.stderr)
        return 1
    if not suggestion_path.is_file():
        print(f"Missing result suggestion in packet: {suggestion_path}", file=sys.stderr)
        return 1

    request = read_json(request_path)
    suggestion = read_json(suggestion_path)

    phase = str(request.get("phase", "")).strip()
    if not phase:
        print(f"Missing phase in {request_path}", file=sys.stderr)
        return 1

    status = args.status if args.status != "auto" else str(suggestion.get("suggested_result_status", "")).strip()
    summary = args.summary or str(suggestion.get("suggested_summary", "")).strip()
    if not status:
        print(f"Missing result status suggestion in {suggestion_path}; pass --status explicitly.", file=sys.stderr)
        return 1
    if not summary:
        print(f"Missing summary suggestion in {suggestion_path}; pass --summary explicitly.", file=sys.stderr)
        return 1

    evidence_paths = [
        str(path)
        for path in [
            packet_dir / "summary.md",
            packet_dir / "response.md",
            packet_dir / "stdout.log",
            packet_dir / "stderr.log",
            packet_dir / "result-suggestion.md",
        ]
        if path.exists()
    ]

    record_command = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "supernb-record-result.py"),
        "--initiative-id",
        initiative_id,
        "--phase",
        phase,
        "--status",
        status,
        "--summary",
        summary,
        "--notes-file",
        str(packet_dir / "summary.md"),
    ]
    for evidence_path in evidence_paths:
        record_command.extend(["--artifact-path", evidence_path])
    if args.no_rerun or args.certify or args.apply_certification:
        record_command.append("--no-rerun")

    subprocess.run(record_command, check=True)

    if args.certify or args.apply_certification:
        certify_command = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "supernb-certify-phase.py"),
            "--initiative-id",
            initiative_id,
            "--phase",
            phase,
        ]
        if args.apply_certification:
            certify_command.extend(["--apply", "--actor", args.actor])
            if args.date:
                certify_command.extend(["--date", args.date])
        subprocess.run(certify_command, check=True)

    if not args.no_rerun and not args.apply_certification:
        subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "supernb-run.py"), "--initiative-id", initiative_id], check=True)

    print(f"Applied execution packet: {packet_dir}")
    print(f"Recorded result status: {status}")
    print(f"Summary: {summary}")
    if args.certify or args.apply_certification:
        print(f"Certification run: yes ({'apply' if args.apply_certification else 'check-only'})")
    else:
        print("Certification run: no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
