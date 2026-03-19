#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from lib.supernb_common import artifact_path as common_artifact_path, load_spec, resolve_spec_path as common_resolve_spec_path

ROOT_DIR = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or delete stale initiative artifacts such as dry-run packets and old command briefs.")
    parser.add_argument("--initiative-id", help="Existing initiative id")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--apply", action="store_true", help="Actually delete the selected artifacts. Defaults to preview only.")
    parser.add_argument("--keep-command-briefs", type=int, default=10, help="How many archived command briefs to keep")
    parser.add_argument("--keep-executions-per-phase", type=int, default=3, help="How many non-preview execution packets to keep per phase")
    parser.add_argument("--prune-phase-results", action="store_true", help="Also prune older phase-result records")
    parser.add_argument("--keep-phase-results-per-phase", type=int, default=20, help="How many phase-result records to keep per phase when pruning")
    return parser.parse_args()


def artifact_path(spec: dict[str, Any], key: str) -> Path:
    return common_artifact_path(spec, key, ROOT_DIR)


def resolve_spec_path(args: argparse.Namespace) -> Path:
    return common_resolve_spec_path(args, ROOT_DIR)


def execution_metadata(packet: Path) -> dict[str, Any]:
    request_path = packet / "request.json"
    suggestion_path = packet / "result-suggestion.json"
    request: dict[str, Any] = {}
    suggestion: dict[str, Any] = {}
    if request_path.is_file():
        try:
            request = json.loads(request_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            request = {}
    if suggestion_path.is_file():
        try:
            suggestion = json.loads(suggestion_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            suggestion = {}
    return {
        "path": packet,
        "phase": str(request.get("phase", "")).strip(),
        "dry_run": bool(request.get("dry_run")),
        "execution_status": str(suggestion.get("execution_status", "")).strip().lower(),
    }


def phase_from_result_name(path: Path) -> str:
    for phase in ["research", "prd", "design", "planning", "delivery", "release"]:
        if f"-{phase}-" in path.name:
            return phase
    return "unknown"


def sorted_desc(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=lambda item: item.stat().st_mtime, reverse=True)


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


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
    initiative_id = str(spec.get("initiative", {}).get("id", "")).strip() or args.initiative_id
    if not initiative_id:
        print(f"Could not determine initiative id from {spec_path}", file=sys.stderr)
        return 1

    command_briefs_dir = artifact_path(spec, "command_briefs_dir")
    executions_dir = artifact_path(spec, "executions_dir")
    phase_results_dir = artifact_path(spec, "phase_results_dir")

    candidates: list[tuple[Path, str]] = []

    if command_briefs_dir.is_dir():
        briefs = sorted_desc([path for path in command_briefs_dir.iterdir() if path.is_file()])
        for path in briefs[args.keep_command_briefs :]:
            candidates.append((path, f"old-command-brief (keep newest {args.keep_command_briefs})"))

    execution_groups: dict[str, list[Path]] = defaultdict(list)
    if executions_dir.is_dir():
        execution_packets = sorted_desc([path for path in executions_dir.iterdir() if path.is_dir()])
        for packet in execution_packets:
            metadata = execution_metadata(packet)
            if metadata["dry_run"]:
                candidates.append((packet, "dry-run-execution-packet"))
                continue
            if metadata["execution_status"] == "unsupported":
                candidates.append((packet, "unsupported-execution-packet"))
                continue
            phase = metadata["phase"] or "unknown"
            execution_groups[phase].append(packet)
        for phase, packets in execution_groups.items():
            for packet in sorted_desc(packets)[args.keep_executions_per_phase :]:
                candidates.append((packet, f"old-execution-packet phase={phase} (keep newest {args.keep_executions_per_phase})"))

    if args.prune_phase_results and phase_results_dir.is_dir():
        result_groups: dict[str, list[Path]] = defaultdict(list)
        for path in sorted_desc([item for item in phase_results_dir.iterdir() if item.is_file()]):
            result_groups[phase_from_result_name(path)].append(path)
        for phase, paths in result_groups.items():
            for path in paths[args.keep_phase_results_per_phase :]:
                candidates.append((path, f"old-phase-result phase={phase} (keep newest {args.keep_phase_results_per_phase})"))

    # Deduplicate while preserving the first reason encountered.
    deduped: list[tuple[Path, str]] = []
    seen: set[Path] = set()
    for path, reason in candidates:
        if path in seen:
            continue
        seen.add(path)
        deduped.append((path, reason))

    print(f"Initiative: {initiative_id}")
    print(f"Mode: {'apply' if args.apply else 'preview'}")
    print(f"Candidates: {len(deduped)}")
    for path, reason in deduped:
        print(f"- {path} :: {reason}")

    if args.apply:
        for path, _reason in deduped:
            remove_path(path)
        print("Cleanup applied.")
    else:
        print("Cleanup preview only. Re-run with --apply to delete the listed artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
