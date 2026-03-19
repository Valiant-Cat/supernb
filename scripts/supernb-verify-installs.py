#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home()
SUPERS_PLUGIN = "superpowers@git+https://github.com/obra/superpowers.git"
KEY_IMPECCABLE_SKILLS = ["audit", "frontend-design", "polish"]
KEY_SUPERPOWERS_SKILLS = ["brainstorming", "executing-plans", "writing-plans"]
HARD_PATH_PATTERNS = [
    (
        "hardcoded absolute harness skill path",
        re.compile(r'/(?:Users|home)/[^/\s"\']+/\.(?:codex|claude|agents|opencode)/skills/[^/\s"\']+/(?:scripts|references|SKILL\.md)'),
    ),
    (
        "hardcoded HOME harness skill path",
        re.compile(r'(?:~|\$HOME)/\.(?:codex|claude|agents|opencode)/skills/[^/\s"\']+/(?:scripts|references|SKILL\.md)'),
    ),
    (
        "hardcoded project-local harness skill path",
        re.compile(r'(?:^|[\s("\'])\.(?:claude|opencode)/skills/[^/\s"\']+/(?:scripts|references|SKILL\.md)'),
    ),
]


@dataclass
class VerificationResult:
    label: str
    status: str
    location: str
    details: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that Codex, Claude Code, and OpenCode installs expose the expected first-level skills."
    )
    parser.add_argument(
        "--harness",
        action="append",
        choices=["codex", "claude-code", "opencode"],
        help="Limit verification to one or more harnesses. Defaults to all.",
    )
    parser.add_argument(
        "--project-dir",
        help="Project directory for project-local Claude Code or OpenCode verification.",
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    text = str(path)
    home = str(HOME_DIR)
    if text == home:
        return "~"
    if text.startswith(home + "/"):
        return "~/" + text[len(home) + 1 :]
    return text


def expected_skill_names(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    names: list[str] = []
    for child in sorted(path.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            names.append(child.name)
    return names


def missing_first_level_skills(base_dir: Path, names: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for name in names:
        if not (base_dir / name / "SKILL.md").is_file():
            missing.append(name)
    return missing


def build_skill_status_line(group: str, expected: list[str], missing: list[str]) -> str:
    found = len(expected) - len(missing)
    line = f"{group}: {found}/{len(expected)} present"
    if missing:
        line += f" | missing: {', '.join(missing)}"
    return line


def verify_first_level_skill_set(
    base_dir: Path,
    supernb_expected: list[str],
    bundled_expected: list[str],
    impeccable_expected: list[str] | None = None,
    superpowers_expected: list[str] | None = None,
) -> list[str]:
    details: list[str] = []
    if not base_dir.is_dir():
        return [f"skills root missing: {display_path(base_dir)}"]

    supernb_missing = missing_first_level_skills(base_dir, supernb_expected)
    bundled_missing = missing_first_level_skills(base_dir, bundled_expected)
    details.append(build_skill_status_line("supernb skills", supernb_expected, supernb_missing))
    details.append(build_skill_status_line("bundled skills", bundled_expected, bundled_missing))

    if superpowers_expected is not None:
        superpowers_missing = missing_first_level_skills(base_dir, superpowers_expected)
        details.append(build_skill_status_line("superpowers key skills", superpowers_expected, superpowers_missing))

    if impeccable_expected is not None:
        impeccable_missing = missing_first_level_skills(base_dir, impeccable_expected)
        details.append(build_skill_status_line("impeccable key skills", impeccable_expected, impeccable_missing))

    return details


def scan_skill_doc_path_hygiene(base_dir: Path, managed_skill_names: Iterable[str]) -> list[str]:
    if not base_dir.is_dir():
        return []

    issues: list[str] = []
    scanned = 0
    for name in managed_skill_names:
        skill_doc = base_dir / name / "SKILL.md"
        if not skill_doc.is_file():
            continue
        scanned += 1
        for line_no, raw_line in enumerate(skill_doc.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            for label, pattern in HARD_PATH_PATTERNS:
                if not pattern.search(stripped):
                    continue
                issues.append(
                    f"{display_path(skill_doc)}:{line_no} {label}: {stripped}"
                )
                break

    if issues:
        details = [f"skill-doc path hygiene: {len(issues)} issue(s) found across {scanned} installed managed skills"]
        details.extend(f"skill-doc path issue: {issue}" for issue in issues)
        return details

    return [f"skill-doc path hygiene: clean across {scanned} installed managed skills"]


def collect_failures(detail_lines: list[str]) -> list[str]:
    failures: list[str] = []
    for line in detail_lines:
        if "missing:" in line or line.startswith("skills root missing:") or line.startswith("skill-doc path issue:"):
            failures.append(line)
    return failures


def parse_claude_plugin_state() -> tuple[str | None, str | None, list[str]]:
    if not shutil_which("claude"):
        return None, None, ["claude CLI not found"]

    proc = subprocess.run(
        ["claude", "plugin", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "claude plugin list failed"
        return None, None, [stderr]

    plugin_id: str | None = None
    plugin_status: str | None = None
    lines = proc.stdout.splitlines()
    for idx, line in enumerate(lines):
        if "superpowers@" not in line:
            continue
        token = next((part for part in line.split() if part.startswith("superpowers@")), None)
        if token:
            plugin_id = token
        for follow in lines[idx + 1 : idx + 5]:
            stripped = follow.strip()
            if stripped.startswith("Status:"):
                if "enabled" in stripped:
                    plugin_status = "enabled"
                elif "disabled" in stripped:
                    plugin_status = "disabled"
                else:
                    plugin_status = stripped.replace("Status:", "").strip()
                break
        break

    if plugin_id is None:
        return None, None, ["Claude Code plugin superpowers is not installed"]
    if plugin_status != "enabled":
        return plugin_id, plugin_status, [f"Claude Code plugin {plugin_id} is not enabled"]
    return plugin_id, plugin_status, []


def shutil_which(binary: str) -> str | None:
    from shutil import which

    return which(binary)


def detect_project_dir(project_dir_arg: str | None) -> Path | None:
    if project_dir_arg:
        return Path(project_dir_arg).expanduser().resolve()

    cwd = Path.cwd()
    if (cwd / ".opencode").exists() or (cwd / "opencode.json").is_file() or (cwd / ".claude" / "skills").is_dir():
        return cwd
    return None


def verify_codex(supernb_expected: list[str], bundled_expected: list[str]) -> VerificationResult:
    base_dir = HOME_DIR / ".agents" / "skills"
    details = verify_first_level_skill_set(
        base_dir=base_dir,
        supernb_expected=supernb_expected,
        bundled_expected=bundled_expected,
        impeccable_expected=KEY_IMPECCABLE_SKILLS,
        superpowers_expected=KEY_SUPERPOWERS_SKILLS,
    )
    details.extend(scan_skill_doc_path_hygiene(base_dir, [*supernb_expected, *bundled_expected]))
    failures = collect_failures(details)
    return VerificationResult(
        label="codex",
        status="pass" if not failures else "fail",
        location=display_path(base_dir),
        details=details,
    )


def verify_claude_user(supernb_expected: list[str], bundled_expected: list[str]) -> VerificationResult:
    base_dir = HOME_DIR / ".claude" / "skills"
    details = verify_first_level_skill_set(
        base_dir=base_dir,
        supernb_expected=supernb_expected,
        bundled_expected=bundled_expected,
        impeccable_expected=KEY_IMPECCABLE_SKILLS,
    )
    details.extend(scan_skill_doc_path_hygiene(base_dir, [*supernb_expected, *bundled_expected]))
    plugin_id, plugin_status, plugin_failures = parse_claude_plugin_state()
    if plugin_id:
        details.append(f"Claude Code plugin: {plugin_id} ({plugin_status or 'unknown'})")
    else:
        details.extend(plugin_failures)

    failures = collect_failures(details) + plugin_failures
    return VerificationResult(
        label="claude-code (user)",
        status="pass" if not failures else "fail",
        location=display_path(base_dir),
        details=details,
    )


def verify_claude_project(project_dir: Path, supernb_expected: list[str], bundled_expected: list[str]) -> VerificationResult:
    base_dir = project_dir / ".claude" / "skills"
    if not base_dir.is_dir():
        return VerificationResult(
            label="claude-code (project)",
            status="skip",
            location=display_path(project_dir),
            details=["project-local Claude Code skills were not found in this project"],
        )

    details = verify_first_level_skill_set(
        base_dir=base_dir,
        supernb_expected=supernb_expected,
        bundled_expected=bundled_expected,
        impeccable_expected=KEY_IMPECCABLE_SKILLS,
    )
    details.extend(scan_skill_doc_path_hygiene(base_dir, [*supernb_expected, *bundled_expected]))
    failures = collect_failures(details)
    return VerificationResult(
        label="claude-code (project)",
        status="pass" if not failures else "fail",
        location=display_path(base_dir),
        details=details,
    )


def verify_opencode(project_dir: Path | None, supernb_expected: list[str], bundled_expected: list[str]) -> VerificationResult:
    if project_dir is None:
        return VerificationResult(
            label="opencode",
            status="skip",
            location="n/a",
            details=["no OpenCode project directory was provided and the current directory is not an OpenCode project"],
        )

    base_dir = project_dir / ".opencode" / "skills"
    config_path = project_dir / "opencode.json"
    details = verify_first_level_skill_set(
        base_dir=base_dir,
        supernb_expected=supernb_expected,
        bundled_expected=bundled_expected,
        impeccable_expected=KEY_IMPECCABLE_SKILLS,
    )
    details.extend(scan_skill_doc_path_hygiene(base_dir, [*supernb_expected, *bundled_expected]))

    plugin_failures: list[str] = []
    if not config_path.is_file():
        plugin_failures.append(f"opencode.json missing: {display_path(config_path)}")
    else:
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            plugin_failures.append(f"opencode.json is invalid JSON: {exc}")
        else:
            plugins = payload.get("plugin", [])
            if isinstance(plugins, str):
                plugins = [plugins]
            if not isinstance(plugins, list):
                plugin_failures.append("opencode.json field 'plugin' is not a string or list")
            elif SUPERS_PLUGIN not in plugins:
                plugin_failures.append(f"missing OpenCode plugin entry: {SUPERS_PLUGIN}")

    if plugin_failures:
        details.extend(plugin_failures)

    failures = collect_failures(details) + plugin_failures
    return VerificationResult(
        label="opencode",
        status="pass" if not failures else "fail",
        location=display_path(base_dir),
        details=details,
    )


def print_result(result: VerificationResult) -> None:
    status_label = {
        "pass": "PASS",
        "fail": "FAIL",
        "skip": "SKIP",
    }[result.status]
    print(f"[{status_label}] {result.label}")
    print(f"  location: {result.location}")
    for detail in result.details:
        print(f"  - {detail}")
    print()


def main() -> int:
    args = parse_args()
    selected = args.harness or ["codex", "claude-code", "opencode"]
    project_dir = detect_project_dir(args.project_dir)
    supernb_expected = expected_skill_names(ROOT_DIR / "skills")
    bundled_expected = expected_skill_names(ROOT_DIR / "bundles" / "skills")

    results: list[VerificationResult] = []

    if "codex" in selected:
        results.append(verify_codex(supernb_expected, bundled_expected))

    if "claude-code" in selected:
        results.append(verify_claude_user(supernb_expected, bundled_expected))
        if project_dir is not None:
            results.append(verify_claude_project(project_dir, supernb_expected, bundled_expected))

    if "opencode" in selected:
        results.append(verify_opencode(project_dir, supernb_expected, bundled_expected))

    for result in results:
        print_result(result)

    passed = sum(1 for result in results if result.status == "pass")
    failed = sum(1 for result in results if result.status == "fail")
    skipped = sum(1 for result in results if result.status == "skip")
    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
