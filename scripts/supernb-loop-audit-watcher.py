#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch a Ralph Loop state file and persist external audit evidence.")
    parser.add_argument("--state-file", required=True, help="Loop state file to watch")
    parser.add_argument("--summary-json", required=True, help="Path to write the loop audit summary JSON")
    parser.add_argument("--events-ndjson", required=True, help="Path to write loop audit events as NDJSON")
    parser.add_argument("--completion-promise", required=True, help="Expected Ralph Loop completion promise")
    parser.add_argument("--max-iterations", type=int, required=True, help="Expected max iteration count")
    parser.add_argument("--expected-session-id", default="", help="Expected Claude Code session id when known")
    parser.add_argument("--poll-interval-seconds", type=float, default=0.5, help="Polling interval while the state file exists")
    parser.add_argument("--timeout-seconds", type=int, default=3600, help="Hard timeout for the audit watcher")
    return parser.parse_args()


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    result: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def parse_iteration(value: str) -> int:
    try:
        return int((value or "0").strip() or "0")
    except ValueError:
        return 0


def normalized_session_id(observed: str, expected: str) -> tuple[str, bool]:
    observed_value = str(observed or "").strip()
    if observed_value:
        return observed_value, False
    expected_value = str(expected or "").strip()
    if expected_value:
        return expected_value, True
    return "", False


def append_event(events_path: Path, payload: dict[str, Any]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def write_summary(summary_path: Path, payload: dict[str, Any]) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_summary(summary_path: Path) -> dict[str, Any] | None:
    if not summary_path.is_file():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def main() -> int:
    args = parse_args()
    state_file = Path(args.state_file).expanduser().resolve()
    summary_path = Path(args.summary_json).expanduser().resolve()
    events_path = Path(args.events_ndjson).expanduser().resolve()
    deadline = time.time() + max(args.timeout_seconds, 1)

    initial_snapshot = parse_frontmatter(state_file) if state_file.is_file() else {}
    initial_observed = bool(initial_snapshot)
    initial_session_id, initial_inferred = normalized_session_id(initial_snapshot.get("session_id", ""), args.expected_session_id)

    summary: dict[str, Any] = {
        "state_file": str(state_file),
        "completion_promise": args.completion_promise,
        "max_iterations": args.max_iterations,
        "expected_session_id": args.expected_session_id,
        "watcher_started_at": utc_now(),
        "watcher_pid": __import__("os").getpid(),
        "state_observed": initial_observed,
        "removed_after_observation": False,
        "last_iteration": parse_iteration(initial_snapshot.get("iteration", "")) if initial_observed else 0,
        "last_session_id": initial_session_id if initial_observed else "",
        "session_id_inferred_from_expected": initial_inferred if initial_observed else False,
        "last_completion_promise": initial_snapshot.get("completion_promise", "") if initial_observed else "",
        "last_started_at": initial_snapshot.get("started_at", "") if initial_observed else "",
        "last_observed_at": utc_now() if initial_observed else "",
        "final_status": "watching",
    }
    write_summary(summary_path, summary)
    append_event(
        events_path,
        {
            "timestamp": utc_now(),
            "event": "watcher-started",
            "state_file": str(state_file),
            "expected_session_id": args.expected_session_id,
            "completion_promise": args.completion_promise,
            "max_iterations": args.max_iterations,
            "state_exists_at_start": state_file.is_file(),
        },
    )

    if initial_observed:
        append_event(
            events_path,
            {
                "timestamp": utc_now(),
                "event": "state-observed",
                "iteration": summary["last_iteration"],
                "session_id": summary["last_session_id"],
                "completion_promise": summary["last_completion_promise"],
                "started_at": summary["last_started_at"],
                "observed_on_start": True,
            },
        )

    last_snapshot: dict[str, str] | None = initial_snapshot or None
    observed_once = initial_observed

    while time.time() < deadline:
        current_summary = read_summary(summary_path)
        if current_summary and str(current_summary.get("final_status", "")).strip() not in {"", "watching"}:
            append_event(
                events_path,
                {
                    "timestamp": utc_now(),
                    "event": "summary-finalized-externally",
                    "final_status": current_summary.get("final_status", ""),
                },
            )
            return 0
        if state_file.is_file():
            current = parse_frontmatter(state_file)
            if current != last_snapshot:
                observed_once = True
                last_snapshot = current
                iteration = parse_iteration(current.get("iteration", ""))
                current_session_id, session_inferred = normalized_session_id(current.get("session_id", ""), args.expected_session_id)
                summary.update(
                    {
                        "state_observed": True,
                        "last_iteration": iteration,
                        "last_session_id": current_session_id,
                        "session_id_inferred_from_expected": session_inferred,
                        "last_completion_promise": current.get("completion_promise", ""),
                        "last_started_at": current.get("started_at", ""),
                        "last_observed_at": utc_now(),
                    }
                )
                write_summary(summary_path, summary)
                append_event(
                    events_path,
                    {
                        "timestamp": utc_now(),
                        "event": "state-observed",
                        "iteration": iteration,
                        "session_id": current.get("session_id", ""),
                        "completion_promise": current.get("completion_promise", ""),
                        "started_at": current.get("started_at", ""),
                    },
                )
        elif observed_once:
            summary.update(
                {
                    "removed_after_observation": True,
                    "last_observed_at": utc_now(),
                    "final_status": "state_removed",
                    "watcher_finished_at": utc_now(),
                }
            )
            write_summary(summary_path, summary)
            append_event(
                events_path,
                {
                    "timestamp": utc_now(),
                    "event": "state-removed",
                    "last_iteration": summary.get("last_iteration", 0),
                },
            )
            return 0

        time.sleep(max(args.poll_interval_seconds, 0.1))

    summary.update(
        {
            "last_observed_at": utc_now(),
            "final_status": "never_observed" if not observed_once else "timeout",
            "watcher_finished_at": utc_now(),
        }
    )
    write_summary(summary_path, summary)
    append_event(
        events_path,
        {
            "timestamp": utc_now(),
            "event": "watcher-timeout",
            "observed_once": observed_once,
            "last_iteration": summary.get("last_iteration", 0),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
