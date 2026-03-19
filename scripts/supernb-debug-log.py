#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.supernb_common import (
    DEBUG_LOG_ENV_VAR,
    debug_log_dir,
    debug_log_enabled,
    debug_log_env_override,
    debug_log_toggle_path,
    load_spec,
    nested_get,
    project_root as common_project_root,
    resolve_spec_path as common_resolve_spec_path,
    utc_now,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enable, disable, or inspect persistent supernb debug logging for a product project.")
    parser.add_argument("action", choices=["on", "off", "status"], help="Toggle state to apply")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--project-dir", help="Product project root. Optional when --spec or --initiative-id can resolve the initiative.")
    return parser.parse_args()


def resolve_spec_path(args: argparse.Namespace) -> Path | None:
    if args.project_dir and not args.spec and not args.initiative_id:
        return None
    return common_resolve_spec_path(args, ROOT_DIR)


def resolve_project(args: argparse.Namespace) -> tuple[Path, Path | None, dict[str, object] | None]:
    if args.project_dir:
        project_dir = Path(args.project_dir).expanduser().resolve()
        spec_path = resolve_spec_path(args) if (args.spec or args.initiative_id) else None
        spec = load_spec(spec_path) if spec_path and spec_path.is_file() else None
        return project_dir, spec_path, spec

    spec_path = resolve_spec_path(args)
    if spec_path is None or not spec_path.is_file():
        raise FileNotFoundError(f"Initiative spec not found: {spec_path}")
    spec = load_spec(spec_path)
    return common_project_root(spec, ROOT_DIR), spec_path, spec


def main() -> int:
    args = parse_args()
    try:
        project_dir, spec_path, spec = resolve_project(args)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    toggle_path = debug_log_toggle_path(project_dir)

    if args.action == "on":
        toggle_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "enabled: true",
            f"enabled_at: {utc_now()}",
        ]
        if spec_path is not None:
            lines.append(f"spec: {spec_path}")
        toggle_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif args.action == "off":
        toggle_path.unlink(missing_ok=True)

    env_override = debug_log_env_override()
    enabled = debug_log_enabled(project_dir)

    print(f"Project dir: {project_dir}")
    print(f"Switch file: {toggle_path}")
    print(f"Debug logging: {'enabled' if enabled else 'disabled'}")
    if spec_path is not None:
        print(f"Spec: {spec_path}")
    if spec is not None:
        initiative_id = nested_get(spec, "initiative", "id")
        if initiative_id:
            print(f"Initiative: {initiative_id}")
        print(f"Initiative log dir: {debug_log_dir(spec, ROOT_DIR)}")
    else:
        print(f"Initiative log dir: enable an initiative-scoped command to start writing under {project_dir / '.supernb'}")

    if env_override is not None:
        print(f"Environment override: {DEBUG_LOG_ENV_VAR}={'1' if env_override else '0'}")
    else:
        print(f"Environment override: not set (persistent switch file controls behavior)")

    if args.action == "on":
        print("Debug logging switch updated: on")
    elif args.action == "off":
        print("Debug logging switch updated: off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
