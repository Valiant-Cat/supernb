#!/usr/bin/env python3

import json
import os
import sys
from typing import Any


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_markdown(path: str, payload: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Update Report")
    lines.append("")
    lines.append(f"- Generated at: `{payload['generated_at']}`")
    lines.append(f"- Repository: `{payload['repository']}`")
    lines.append(f"- Report JSON: `{os.path.basename(payload['report_json'])}`")
    lines.append("")

    self_update = payload["self_update"]
    lines.append("## supernb")
    lines.append("")
    lines.append(f"- Status: `{self_update['status']}`")
    if self_update.get("branch"):
        lines.append(f"- Branch: `{self_update['branch']}`")
    if self_update.get("default_branch"):
        lines.append(f"- Default branch: `{self_update['default_branch']}`")
    if self_update.get("before_commit"):
        lines.append(f"- Before: `{self_update['before_commit']}`")
    if self_update.get("after_commit"):
        lines.append(f"- After: `{self_update['after_commit']}`")
    lines.append(f"- Message: {self_update['message']}")
    lines.append("")

    upstreams = payload["upstreams"]
    lines.append("## Upstreams")
    lines.append("")
    for repo in upstreams["repositories"]:
        lines.append(f"### {repo['name']}")
        lines.append("")
        lines.append(f"- Status: `{repo['status']}`")
        if repo.get("default_branch"):
            lines.append(f"- Default branch: `{repo['default_branch']}`")
        if repo.get("before_commit"):
            lines.append(f"- Before: `{repo['before_commit']}`")
        if repo.get("after_commit"):
            lines.append(f"- After: `{repo['after_commit']}`")
        if repo.get("message"):
            lines.append(f"- Message: {repo['message']}")
        lines.append("")

    build = upstreams["impeccable_build"]
    lines.append("## impeccable Build")
    lines.append("")
    lines.append(f"- Status: `{build['status']}`")
    lines.append(f"- Message: {build['message']}")
    lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "Usage: write-update-report.py <output-dir> <generated-at> <repo-root> <self-json> <upstreams-json>",
            file=sys.stderr,
        )
        return 1

    output_dir, generated_at, repo_root, self_json_path, upstreams_json_path = sys.argv[1:]
    os.makedirs(output_dir, exist_ok=True)

    self_update = load_json(self_json_path)
    upstreams = load_json(upstreams_json_path)

    stamp = generated_at.replace(":", "-")
    json_path = os.path.join(output_dir, f"{stamp}-update-report.json")
    md_path = os.path.join(output_dir, f"{stamp}-update-report.md")

    payload = {
        "generated_at": generated_at,
        "repository": repo_root,
        "report_json": json_path,
        "report_markdown": md_path,
        "self_update": self_update,
        "upstreams": upstreams,
    }

    write_json(json_path, payload)
    write_markdown(md_path, payload)

    print(json.dumps({"json": json_path, "markdown": md_path}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
