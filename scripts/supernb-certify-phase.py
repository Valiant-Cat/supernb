#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
PHASES = ["research", "prd", "design", "planning", "delivery", "release"]

METADATA_FIELDS = {
    "Initiative ID",
    "Product",
    "Research date",
    "Prepared",
    "Status",
    "Approval status",
    "Ready for execution",
    "Delivery status",
    "Release decision",
    "Approved by",
    "Approved on",
}

_EXECUTE_NEXT_MODULE: Any | None = None


@dataclass
class Issue:
    path: Path
    line_no: int
    message: str
    line_text: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Certify whether a phase artifact set looks complete enough to advance.")
    parser.add_argument("--initiative-id", help="Existing initiative id, e.g. 2026-03-19-my-product")
    parser.add_argument("--spec", help="Path to initiative.yaml")
    parser.add_argument("--phase", choices=PHASES, help="Phase to inspect. Defaults to the current selected phase.")
    parser.add_argument("--apply", action="store_true", help="Apply the recommended gate status when the phase passes certification")
    parser.add_argument("--actor", default="supernb", help="Actor name used when --apply is set")
    parser.add_argument("--date", default=today_stamp(), help="Approval date used when --apply is set")
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


def load_execute_next_module() -> Any:
    global _EXECUTE_NEXT_MODULE
    if _EXECUTE_NEXT_MODULE is not None:
        return _EXECUTE_NEXT_MODULE

    module_path = ROOT_DIR / "scripts" / "supernb-execute-next.py"
    module_spec = importlib.util.spec_from_file_location("supernb_execute_next", module_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load execute-next module from {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    _EXECUTE_NEXT_MODULE = module
    return module


def build_phase_readiness(spec: dict[str, Any], phase: str) -> dict[str, Any]:
    module = load_execute_next_module()
    return module.build_phase_readiness(spec, phase)


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


def recommended_gate_status(phase: str) -> str:
    mapping = {
        "research": "approved",
        "prd": "approved",
        "design": "approved",
        "planning": "ready",
        "delivery": "verified",
        "release": "ready",
    }
    return mapping[phase]


def line_is_placeholder_bullet(stripped: str) -> bool:
    match = re.match(r"^- ([^:]+):\s*$", stripped)
    if not match:
        return False
    label = match.group(1).strip()
    return label not in METADATA_FIELDS


def line_is_placeholder_numbered(stripped: str) -> bool:
    return bool(re.match(r"^\d+\.\s+[^:]+:\s*$", stripped))


def line_is_empty_table_row(stripped: str) -> bool:
    if not stripped.startswith("|"):
        return False
    if re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", stripped):
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return all(cell == "" for cell in cells)


def line_has_template_marker(stripped: str) -> bool:
    patterns = [
        r"\bPattern \d+:\s*$",
        r"\bGap \d+:\s*$",
        r"\bJourney \d+:\s*$",
        r"\bGoal \d+:\s*$",
        r"\bNon-goal \d+:\s*$",
        r"\bPage \d+\s*$",
        r"\bHotspot \d+:\s*$",
    ]
    return any(re.search(pattern, stripped) for pattern in patterns)


def line_is_unchecked_release_checkbox(stripped: str, phase: str) -> bool:
    return phase == "release" and stripped.startswith("- [ ] ")


def collect_issues(path: Path, phase: str) -> list[Issue]:
    issues: list[Issue] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if "{{" in stripped and "}}" in stripped:
            issues.append(Issue(path, idx, "Unresolved template variable remains", stripped))
            continue
        if line_is_placeholder_bullet(stripped):
            issues.append(Issue(path, idx, "Blank placeholder field remains", stripped))
            continue
        if line_is_placeholder_numbered(stripped):
            issues.append(Issue(path, idx, "Blank numbered placeholder remains", stripped))
            continue
        if line_is_empty_table_row(stripped):
            issues.append(Issue(path, idx, "Empty table row remains", stripped))
            continue
        if line_has_template_marker(stripped) and stripped.endswith(":"):
            issues.append(Issue(path, idx, "Template marker still present", stripped))
            continue
        if line_is_unchecked_release_checkbox(stripped, phase):
            issues.append(Issue(path, idx, "Unchecked release checklist item remains", stripped))
    return issues


def append_run_log(
    log_path: Path,
    phase: str,
    recommendation: str,
    passed: bool,
    applied: bool,
    report_path: Path,
) -> None:
    if not log_path.exists():
        log_path.write_text("# Run Log\n\n", encoding="utf-8")
    lines = [
        f"## {utc_now()} certification",
        "",
        f"- Phase: `{phase}`",
        f"- Passed: `{'yes' if passed else 'no'}`",
        f"- Recommended gate status: `{recommendation}`",
        f"- Applied automatically: `{'yes' if applied else 'no'}`",
        f"- Certification report: `{display_path(report_path)}`",
        "",
    ]
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def write_report(
    spec: dict[str, Any],
    phase: str,
    issues: list[Issue],
    readiness: dict[str, Any],
    report_path: Path,
    applied: bool,
) -> None:
    recommendation = recommended_gate_status(phase)
    readiness_ok = bool(readiness.get("ready_for_certification"))
    lines = [
        "# Phase Certification",
        "",
        f"- Initiative ID: `{nested_get(spec, 'initiative', 'id')}`",
        f"- Phase: `{phase}`",
        f"- Recorded: `{utc_now()}`",
        f"- Passed: `{'yes' if not issues and readiness_ok else 'no'}`",
        f"- Recommended gate status: `{recommendation}`",
        f"- Applied automatically: `{'yes' if applied else 'no'}`",
        "",
        "## Checked Artifacts",
        "",
    ]
    for target in phase_targets(spec, phase):
        lines.append(f"- `{display_path(target)}`")

    lines.extend(
        [
            "",
            "## Phase Readiness",
            "",
            f"- Ready for certification: `{'yes' if readiness_ok else 'no'}`",
            f"- Summary: {readiness.get('summary', '')}",
            f"- Missing sections: `{readiness.get('total_missing_sections', 0)}`",
            f"- Thin sections: `{readiness.get('total_thin_sections', 0)}`",
            f"- Placeholder lines: `{readiness.get('total_placeholders', 0)}`",
            f"- Semantic issues: `{readiness.get('total_semantic_issues', 0)}`",
        ]
    )

    lines.extend(["", "## Findings", ""])
    if issues:
        for issue in issues:
            lines.append(f"- `{display_path(issue.path)}:{issue.line_no}` {issue.message}: `{issue.line_text}`")
    for check in readiness.get("artifact_checks", []):
        if check.get("missing_sections"):
            lines.append(f"- `{check['path']}` missing sections: {', '.join(check['missing_sections'])}")
        if check.get("thin_sections"):
            lines.append(f"- `{check['path']}` thin sections: {', '.join(check['thin_sections'])}")
        for semantic_issue in check.get("semantic_issues", []):
            lines.append(f"- `{check['path']}` semantic gap: {semantic_issue}")
    if not issues and readiness_ok:
        lines.append("- No unresolved template placeholders, missing sections, thin sections, or semantic readiness gaps were detected.")

    lines.extend(["", "## Next Action", ""])
    if issues or not readiness_ok:
        lines.append(f"- Resolve the findings above, then rerun `./scripts/supernb certify-phase --initiative-id {nested_get(spec, 'initiative', 'id')} --phase {phase}`.")
    elif applied:
        lines.append(f"- The gate was advanced automatically to `{recommendation}`.")
    else:
        lines.append(f"- You can now advance the gate with `./scripts/supernb advance-phase --initiative-id {nested_get(spec, 'initiative', 'id')} --phase {phase} --status {recommendation} --actor <who approved it>`.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    issues: list[Issue] = []
    for target in phase_targets(spec, phase):
        if not target.is_file():
            print(f"Artifact not found for phase {phase}: {target}", file=sys.stderr)
            return 1
        issues.extend(collect_issues(target, phase))
    readiness = build_phase_readiness(spec, phase)
    passed = not issues and bool(readiness.get("ready_for_certification"))

    results_dir = artifact_path(spec, "phase_results_dir")
    run_log_path = artifact_path(spec, "run_log_md")
    results_dir.mkdir(parents=True, exist_ok=True)
    report_path = results_dir / f"{timestamp_slug()}-{phase}-certification.md"

    applied = False
    if args.apply and passed:
        subprocess.run(
            [
                sys.executable,
                str(ROOT_DIR / "scripts" / "supernb-advance-phase.py"),
                "--initiative-id",
                initiative_id,
                "--phase",
                phase,
                "--status",
                recommended_gate_status(phase),
                "--actor",
                args.actor,
                "--date",
                args.date,
            ],
            check=True,
        )
        applied = True

    write_report(spec, phase, issues, readiness, report_path, applied)
    append_run_log(run_log_path, phase, recommended_gate_status(phase), passed, applied, report_path)

    print(f"Phase certification report: {report_path}")
    print(f"Passed: {'yes' if passed else 'no'}")
    print(f"Recommended gate status: {recommended_gate_status(phase)}")
    if not passed:
        print(f"Line issue count: {len(issues)}")
        print(
            "Readiness gaps: "
            f"missing={readiness.get('total_missing_sections', 0)} "
            f"thin={readiness.get('total_thin_sections', 0)} "
            f"placeholders={readiness.get('total_placeholders', 0)} "
            f"semantic={readiness.get('total_semantic_issues', 0)}"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
