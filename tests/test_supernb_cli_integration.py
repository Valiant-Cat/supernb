from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )


def run_command(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd or ROOT_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def write_fake_claude(bin_dir: Path) -> Path:
    script_path = bin_dir / "claude"
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            import re
            import sys
            import time
            from pathlib import Path

            args = sys.argv[1:]
            plugin_id = os.environ.get("FAKE_CLAUDE_PLUGIN_ID", "supernb-loop@supernb")
            plugin_status = os.environ.get("FAKE_CLAUDE_PLUGIN_STATUS", "enabled")

            if args[:2] == ["plugin", "list"]:
                print(plugin_id)
                print("  Version: 1.0.0")
                print("  Scope: User")
                print(f"  Status: {plugin_status}")
                sys.exit(0)

            if "-p" in args:
                prompt = sys.stdin.read()
                loop_delete_delay = float(os.environ.get("FAKE_CLAUDE_LOOP_DELETE_DELAY", "0.8"))

                def extract(pattern: str) -> str:
                    match = re.search(pattern, prompt, re.DOTALL)
                    return match.group(1).strip() if match else ""

                state_file = extract(r"state file `([^`]+)`")
                audit_summary = extract(r"External audit summary: `([^`]+)`")
                completion_promise = extract(r"final response must include `<promise>(.*?)</promise>`")
                if not completion_promise:
                    promise_matches = re.findall(r"<promise>(.*?)</promise>", prompt, re.DOTALL)
                    if promise_matches:
                        completion_promise = promise_matches[-1].strip()

                if state_file:
                    time.sleep(max(loop_delete_delay, 0.0))
                    state_path = Path(state_file)
                    if state_path.exists():
                        state_path.unlink()

                report = {
                    "completion_status": "completed",
                    "summary": "Completed the requested Claude Code batch.",
                    "completed_items": ["Finished the requested Claude Code batch."],
                    "remaining_items": [],
                    "evidence_artifacts": [audit_summary] if audit_summary else [],
                    "artifacts_updated": [],
                    "commands_run": [],
                    "tests_run": [],
                    "validated_batches_completed": 0,
                    "batch_commits": [],
                    "workflow_trace": {
                        "brainstorming": {"used": False, "evidence": "Not needed."},
                        "writing_plans": {"used": True, "evidence": "Updated the current plan."},
                        "test_driven_development": {"used": False, "evidence": "Not needed for this planning batch."},
                        "code_review": {"used": False, "evidence": "Not needed for this planning batch."},
                        "using_git_worktrees": {"used": False, "evidence": "Not needed."},
                        "subagent_or_executing_plans": {"used": True, "evidence": "Executed the bounded planning batch."},
                    },
                    "loop_execution": {
                        "used": bool(audit_summary),
                        "mode": "ralph-loop" if audit_summary else "none",
                        "completion_promise": completion_promise,
                        "state_file": state_file,
                        "max_iterations": 6,
                        "final_iteration": 1 if audit_summary else 0,
                        "exit_reason": "completion promise became true" if audit_summary else "",
                        "evidence": audit_summary,
                    },
                    "recommended_result_status": "succeeded",
                    "recommended_gate_action": "certify",
                    "recommended_gate_status": "ready",
                    "follow_up": [],
                }

                print("Completed the requested Claude Code batch.")
                print("SUPERNB_EXECUTION_REPORT_JSON_START")
                print(json.dumps(report, indent=2))
                print("SUPERNB_EXECUTION_REPORT_JSON_END")
                if completion_promise:
                    print(f"<promise>{completion_promise}</promise>")
                sys.exit(0)

            print("unsupported fake claude invocation", file=sys.stderr)
            sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def write_fake_claude_for_install(bin_dir: Path, log_path: Path) -> Path:
    script_path = bin_dir / "claude"
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            log_path = Path(os.environ["FAKE_CLAUDE_INSTALL_LOG"])
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(" ".join(args) + "\\n")

            if args[:3] == ["plugin", "marketplace", "add"]:
                sys.exit(0)
            if args[:3] == ["plugin", "enable", "supernb-loop@supernb"]:
                sys.exit(1)
            if args[:3] == ["plugin", "install", "supernb-loop@supernb"]:
                sys.exit(0)
            if args[:2] == ["plugin", "list"]:
                sys.exit(0)

            print("unsupported fake install claude invocation", file=sys.stderr)
            sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def write_fake_claude_for_prompt_first(bin_dir: Path, log_path: Path) -> Path:
    script_path = bin_dir / "claude"
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            log_path = Path(os.environ["FAKE_CLAUDE_INSTALL_LOG"])
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(" ".join(args) + "\\n")

            if args[:3] == ["plugin", "marketplace", "add"]:
                sys.exit(0)
            if args[:3] == ["plugin", "enable", "supernb-loop@supernb"]:
                sys.exit(0)
            if args[:3] == ["plugin", "install", "supernb-loop@supernb"]:
                sys.exit(0)
            if args[:2] == ["plugin", "list"]:
                print("supernb-loop@supernb")
                print("  Version: 1.0.0")
                print("  Scope: User")
                print("  Status: enabled")
                sys.exit(0)

            print("unsupported fake prompt-first claude invocation", file=sys.stderr)
            sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)
    return script_path


def write_fake_git_for_remote_install(bin_dir: Path, clone_source: Path) -> Path:
    script_path = bin_dir / "git"
    script_path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import shutil
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            clone_source = Path(sys.argv[0]).resolve().parent / "fake-git-clone-source"

            if args[:1] == ["clone"] and len(args) >= 3:
                target = Path(args[-1]).resolve()
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(clone_source, target)
                (target / ".git").mkdir(parents=True, exist_ok=True)
                sys.exit(0)

            if args[:1] == ["pull"]:
                sys.exit(0)

            print("unsupported fake git invocation", file=sys.stderr)
            sys.exit(1)
            """
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o755)

    clone_link = bin_dir / "fake-git-clone-source"
    if clone_link.exists() or clone_link.is_symlink():
        clone_link.unlink()
    clone_link.symlink_to(clone_source, target_is_directory=True)
    return script_path


def write_spec(root: Path, initiative_id: str = "2026-03-19-demo") -> dict[str, Path]:
    project_dir = root / "product"
    initiative_root = project_dir / ".supernb" / "initiatives" / initiative_id
    spec_path = initiative_root / "initiative.yaml"
    research_dir = project_dir / ".supernb" / "research" / initiative_id
    prd_dir = project_dir / ".supernb" / "prd" / initiative_id
    design_dir = project_dir / ".supernb" / "design" / initiative_id
    plan_dir = project_dir / ".supernb" / "plans" / initiative_id
    release_dir = project_dir / ".supernb" / "releases" / initiative_id
    command_briefs_dir = initiative_root / "command-briefs"
    phase_results_dir = initiative_root / "phase-results"
    executions_dir = initiative_root / "executions"

    for directory in [
        initiative_root,
        research_dir,
        prd_dir,
        design_dir,
        plan_dir,
        release_dir,
        command_briefs_dir,
        phase_results_dir,
        executions_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    spec_text = f"""
initiative:
  id: "{initiative_id}"
delivery:
  project_dir: "{project_dir}"
artifacts:
  run_status_md: ".supernb/initiatives/{initiative_id}/run-status.md"
  run_status_json: ".supernb/initiatives/{initiative_id}/run-status.json"
  run_log_md: ".supernb/initiatives/{initiative_id}/run-log.md"
  initiative_index: ".supernb/initiatives/{initiative_id}.md"
  next_command_md: ".supernb/initiatives/{initiative_id}/next-command.md"
  phase_packet_md: ".supernb/initiatives/{initiative_id}/phase-packet.md"
  command_briefs_dir: ".supernb/initiatives/{initiative_id}/command-briefs"
  phase_results_dir: ".supernb/initiatives/{initiative_id}/phase-results"
  executions_dir: ".supernb/initiatives/{initiative_id}/executions"
  certification_state_json: ".supernb/initiatives/{initiative_id}/certification-state.json"
  research_dir: ".supernb/research/{initiative_id}"
  prd_dir: ".supernb/prd/{initiative_id}"
  design_dir: ".supernb/design/{initiative_id}"
  plan_dir: ".supernb/plans/{initiative_id}"
  release_dir: ".supernb/releases/{initiative_id}"
""".strip()
    spec_path.write_text(spec_text + "\n", encoding="utf-8")

    return {
        "project_dir": project_dir,
        "initiative_root": initiative_root,
        "spec_path": spec_path,
        "research_dir": research_dir,
        "prd_dir": prd_dir,
        "design_dir": design_dir,
        "plan_dir": plan_dir,
        "release_dir": release_dir,
        "command_briefs_dir": command_briefs_dir,
        "phase_results_dir": phase_results_dir,
        "executions_dir": executions_dir,
    }


def write_report_json(
    path: Path,
    evidence_artifacts: list[str] | None = None,
    completion_status: str = "completed",
    recommended_result_status: str = "succeeded",
    recommended_gate_action: str = "certify",
    recommended_gate_status: str = "ready",
) -> None:
    payload = {
        "completion_status": completion_status,
        "summary": "Imported execution completed.",
        "completed_items": ["Finished the requested work."],
        "remaining_items": [],
        "evidence_artifacts": evidence_artifacts or [],
        "artifacts_updated": [],
        "commands_run": [],
        "tests_run": [],
        "validated_batches_completed": 1,
        "batch_commits": [],
        "workflow_trace": {
            "brainstorming": {"used": False, "evidence": "Not used in this imported handoff."},
            "writing_plans": {"used": False, "evidence": "No planning workflow was needed for this imported handoff."},
            "test_driven_development": {"used": False, "evidence": "No code-delivery loop was executed in this imported handoff."},
            "code_review": {"used": False, "evidence": "No code review was part of this imported handoff."},
            "using_git_worktrees": {"used": False, "evidence": "No git worktree workflow was used."},
            "subagent_or_executing_plans": {"used": False, "evidence": "No delegated execution workflow was used."},
        },
        "recommended_result_status": recommended_result_status,
        "recommended_gate_action": recommended_gate_action,
        "recommended_gate_status": recommended_gate_status,
        "follow_up": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_planning_traceability_artifacts(paths: dict[str, Path], initiative_id: str) -> None:
    prd_path = paths["prd_dir"] / "product-requirements.md"
    design_path = paths["design_dir"] / "ui-ux-spec.md"
    plan_path = paths["plan_dir"] / "implementation-plan.md"
    for path in [prd_path, design_path, plan_path]:
        path.parent.mkdir(parents=True, exist_ok=True)

    prd_path.write_text(
        textwrap.dedent(
            f"""\
            # Product Requirements

            - Initiative ID: `{initiative_id}`
            - Product: `Demo Product`
            - Prepared: `2026-03-20`
            - Approval status: approved
            - Approved by: `supernb`
            - Approved on: `2026-03-20`

            ## Cross-Phase Traceability Matrix

            | Trace ID | PRD capability | Primary design surface | Research insight or review theme |
            | --- | --- | --- | --- |
            | TR-001 | Guided onboarding | Onboarding flow | Setup friction |
            | TR-002 | Trust-first paywall timing | Premium upsell | Premium value clarity |
            | TR-003 | Daily return reminder loop | Home dashboard | Repeat usage habit |
            | TR-004 | Recovery and error guidance | Error recovery | Trust and support |
            """
        ),
        encoding="utf-8",
    )

    design_path.write_text(
        textwrap.dedent(
            f"""\
            # UI UX Spec

            - Initiative ID: `{initiative_id}`
            - Product: `Demo Product`
            - Prepared: `2026-03-20`
            - Approval status: approved
            - Approved by: `supernb`
            - Approved on: `2026-03-20`

            ## Traceability To Research And PRD

            | Trace ID | PRD capability | Primary design surface | Research insight reference |
            | --- | --- | --- | --- |
            | TR-001 | Guided onboarding | Onboarding flow | Setup friction |
            | TR-002 | Trust-first paywall timing | Premium upsell | Premium value clarity |
            | TR-003 | Daily return reminder loop | Home dashboard | Repeat usage habit |
            | TR-004 | Recovery and error guidance | Error recovery | Trust and support |
            """
        ),
        encoding="utf-8",
    )

    plan_path.write_text(
        textwrap.dedent(
            f"""\
            # Implementation Plan

            - Initiative ID: `{initiative_id}`
            - Product: `Demo Product`
            - Prepared: `2026-03-20`
            - Ready for execution: yes
            - Delivery status: pending
            - Approved by: `supernb`
            - Approved on: `2026-03-20`

            ## Scope For This Plan

            - Included: Guided onboarding hardening, premium timing rules, habit loop instrumentation, and recovery UX.
            - Excluded: New pricing experiments outside the approved scope.

            ## Architecture And Technical Strategy

            - Core implementation approach: Extend the existing onboarding and dashboard flows in bounded batches with test-first updates.
            - Key modules or services involved: onboarding controller, paywall presenter, home dashboard state, and error recovery components.
            - Data model or contract impact: Add onboarding completion, reminder eligibility, and recovery telemetry fields.
            - Technical risks to control early: Session state drift, localization regressions, and incomplete trust instrumentation.

            ## Milestones

            | Milestone | Outcome | Exit criteria |
            | --- | --- | --- |
            | Planning complete | Delivery can start from bounded batches | Batches, verification, and traceability are all filled |

            ## Dependency And Risk Map

            | Area | Dependency or risk | Why it matters | Mitigation |
            | --- | --- | --- | --- |
            | Onboarding state | Existing session restore logic | Can regress activation continuity | Add regression tests before wiring new fields |
            | Paywall timing | Existing premium trigger rules | Wrong trigger harms trust | Gate with scenario tests and review copy timing |

            ## Task Batches

            ### Batch 1

            - Goal: Harden the onboarding path and activation telemetry.
            - Dependencies: Existing onboarding controller and session restore hooks.
            - Test-first tasks: Add failing onboarding activation and persistence tests before implementation.
            - Verification: Run onboarding unit tests and activation flow smoke checks.

            ### Batch 2

            - Goal: Align premium timing and dashboard habit loop prompts with the approved design surfaces.
            - Dependencies: Premium presenter, dashboard cards, and reminder scheduler.
            - Test-first tasks: Add failing paywall timing and reminder eligibility tests before implementation.
            - Verification: Run paywall rule tests, dashboard integration tests, and lint checks.

            ### Batch 3

            - Goal: Finalize recovery UX and release-facing evidence capture.
            - Dependencies: Error recovery surfaces and release readiness updates.
            - Test-first tasks: Add failing recovery state and retry affordance tests before implementation.
            - Verification: Run recovery UI tests and release-readiness consistency checks.

            ## Localization Work

            - Hardcoded string extraction tasks: Move onboarding, paywall, reminder, and recovery copy into localization resources.
            - Source locale key creation: Add stable source keys for every new user-facing string.
            - Target locale sync: Sync translated keys for required launch locales before merge.
            - Translation completion workflow: Use the managed localization workflow before final batch closeout.

            ## Review And Verification Cadence

            - When code review runs: Review every validated batch before commit.
            - Required verification before each commit: Run unit, integration, and copy-governance checks for the touched surfaces.
            - Batch completion evidence format: Record commands, tests, commits, and artifact updates in the execution report.
            - When to update initiative artifacts: Refresh plan and release evidence after each validated batch.

            ## Loop Candidates

            Use Frad loop mode only for bounded tasks.

            | Task | Why loop helps | Completion promise | Max iterations |
            | --- | --- | --- | --- |
            | Planning closeout | Prevents self-judged stop before certification | SUPERNB {initiative_id} planning batch complete | 6 |

            ## Verification Commands

            ```bash
            ./scripts/check-no-hardcoded-copy.sh
            npm test -- --runInBand
            npm run lint
            ```

            ## Commit Strategy

            - Commit frequency: One commit per validated batch.
            - Branch strategy: Stay on the active feature branch for the bounded delivery stream.
            - PR strategy: Keep one reviewable PR that aggregates the validated planning-to-delivery batches.

            ## Rollout And Recovery Plan

            - Release unit for this work: Onboarding, premium timing, dashboard reminders, and recovery UX ship together.
            - Rollback or recovery strategy: Disable the new timing rules behind the existing configuration toggle if regressions appear.
            - Observability or monitoring checks: Track onboarding completion, paywall conversion, reminder acceptance, and retry success.
            - Post-merge validation: Run smoke validation across onboarding, dashboard, premium, and recovery entry points.

            ## Scale And Reliability Workstreams

            - Performance and capacity work: Keep onboarding and dashboard interactions within current frame-budget targets.
            - Analytics and experimentation work: Instrument activation, premium timing, reminder, and recovery funnel checkpoints.
            - Abuse / fraud / trust safeguards: Preserve billing trust cues and avoid misleading premium timing behavior.
            - Observability and incident readiness: Add dashboard and recovery alerts for broken activation or retry flows.
            - Growth surface instrumentation: Measure reminder-driven return behavior and premium conversion entry points.

            ## Delivery Traceability Map

            Carry the same launch-critical capabilities from the PRD/design traceability matrix into concrete delivery batches and verification. Reuse the same Trace ID values so delivery can be audited row by row.

            | Trace ID | PRD capability | Design surface | Delivery batch | Verification evidence | Release dependency |
            | --- | --- | --- | --- | --- | --- |
            | TR-001 | Guided onboarding | Onboarding flow | Batch 1 | onboarding activation tests | Activation smoke pass |
            | TR-002 | Trust-first paywall timing | Premium upsell | Batch 2 | paywall timing tests | Billing trust review |
            | TR-003 | Daily return reminder loop | Home dashboard | Batch 2 | dashboard reminder tests | Reminder analytics check |
            | TR-004 | Recovery and error guidance | Error recovery | Batch 3 | retry and recovery tests | Incident readiness review |
            """
        ),
        encoding="utf-8",
    )


def write_research_artifacts_for_certification(project_dir: Path, initiative_id: str) -> None:
    research_dir = project_dir / ".supernb" / "research" / initiative_id
    research_dir.mkdir(parents=True, exist_ok=True)

    (research_dir / "01-competitor-landscape.md").write_text(
        "# Competitor Landscape\n\n"
        f"- Initiative ID: `{initiative_id}`\n"
        "- Product: `Demo Product`\n"
        "- Research date: `2026-03-19`\n"
        "- Status: pending\n\n"
        "- Approved by:\n"
        "- Approved on:\n\n"
        "## Research Window\n\n"
        "- Stores: App Store, Google Play\n"
        "- Countries: US, JP, BR\n"
        "- Languages sampled: en, ja, pt-BR\n"
        "- Start date: 2025-12-01\n"
        "- End date: 2026-03-01\n\n"
        "## Competitor Shortlist\n\n"
        "| Competitor | Store | Market | Why it matters |\n"
        "| --- | --- | --- | --- |\n"
        "| Alpha | App Store | US | Category leader |\n"
        "| Beta | Google Play | JP | Strong retention |\n"
        "| Gamma | App Store | BR | Price-sensitive growth |\n\n"
        "## Feature Surface Comparison\n\n"
        "| Feature | Alpha | Beta | Gamma |\n"
        "| --- | --- | --- | --- |\n"
        "| Guided onboarding | Yes | Yes | Partial |\n"
        "| Personalized feed | Yes | Yes | Yes |\n"
        "| Social proof | Partial | Yes | No |\n\n"
        "## Metadata Snapshot\n\n"
        "| App | Rating | Reviews | Notes |\n"
        "| --- | --- | --- | --- |\n"
        "| Alpha | 4.7 | 120k | Premium positioning |\n"
        "| Beta | 4.6 | 88k | Strong habit loop |\n"
        "| Gamma | 4.4 | 41k | Price-led growth |\n\n"
        "## Monetization And Packaging\n\n"
        "| App | Monetization | Packaging | Observation |\n"
        "| --- | --- | --- | --- |\n"
        "| Alpha | Subscription | Premium annual plan | Strong trial funnel |\n"
        "| Beta | Freemium + add-ons | Hybrid plan | Monetizes power users |\n\n"
        "## Regional And Segment Signals\n\n"
        "| Market or segment | Signal | Why it matters |\n"
        "| --- | --- | --- |\n"
        "| Japan | Trust and polish are emphasized | Quality expectations are high |\n"
        "| Brazil | Pricing sensitivity is explicit | Offer design matters |\n\n"
        "## Scale Signals And Market Headroom\n\n"
        "- Total demand or category headroom signal: Large cross-store category demand with top players sustaining scale.\n"
        "- Evidence of cross-market repeatability: Similar onboarding and retention patterns show up in US, JP, and BR.\n"
        "- Evidence of high-frequency usage: Review language references daily or weekly repeat behavior.\n"
        "- Distribution or acquisition pattern: Editorial featuring and creator sharing both appear repeatedly.\n"
        "- Operational complexity signal: Content freshness and support responsiveness are major quality levers.\n\n"
        "## Observed Strategic Patterns\n\n"
        "- Pattern 1: Leaders simplify onboarding before asking for commitment.\n"
        "- Pattern 2: High-retention apps reinforce daily return loops quickly.\n"
        "- Pattern 3: Premium conversion happens after clear personalized value appears.\n"
        "- Pattern 4: Trust cues are visible around data, billing, and error recovery.\n"
        "- Pattern 5: Localized packaging changes by market maturity.\n\n"
        "## Gaps To Investigate\n\n"
        "- Gap 1: Which trust cue matters most in first session conversion?\n"
        "- Gap 2: How much localization depth changes activation by market?\n"
        "- Gap 3: Which premium lever is least disruptive to habit formation?\n\n"
        "## Raw Data References\n\n"
        "- Sensor Tower export: competitor-landscape.csv\n"
        "- Notes: market-scan-notes.md\n"
        "- Additional links or screenshots: screenshot-bundle.zip\n",
        encoding="utf-8",
    )

    (research_dir / "02-review-insights.md").write_text(
        "# Review Insights\n\n"
        f"- Initiative ID: `{initiative_id}`\n"
        "- Product: `Demo Product`\n"
        "- Research date: `2026-03-19`\n"
        "- Status: pending\n\n"
        "- Approved by:\n"
        "- Approved on:\n\n"
        "## Query Context\n\n"
        "- Apps reviewed: Alpha, Beta, Gamma\n"
        "- Countries: US, JP, BR\n"
        "- Languages reviewed: en, ja, pt-BR\n"
        "- Date window: 2025-12-01 to 2026-03-01\n"
        "- Total reviews: 2500+\n"
        "- Regional coverage rationale: Covers mature, premium, and value-sensitive markets.\n\n"
        "## Top Complaint Clusters\n\n"
        "| Complaint | Frequency | Why it matters |\n"
        "| --- | --- | --- |\n"
        "| Setup feels confusing | High | Breaks activation |\n"
        "| Premium value is unclear | Medium | Hurts conversion |\n"
        "| Support response is slow | Medium | Damages trust |\n\n"
        "## Top Delight Clusters\n\n"
        "| Delight | Frequency | Why it matters |\n"
        "| --- | --- | --- |\n"
        "| Personalized recommendations feel useful | High | Drives return usage |\n"
        "| Clean interface reduces effort | Medium | Supports habit formation |\n\n"
        "## Jobs Users Are Hiring The Product To Do\n\n"
        "| Job | Trigger | Desired outcome |\n"
        "| --- | --- | --- |\n"
        "| Get oriented fast | First session | Understand value quickly |\n"
        "| Check progress regularly | Daily return | Stay on track with confidence |\n\n"
        "## Explicit Feature Requests\n\n"
        "| Request | Why users ask for it | Opportunity |\n"
        "| --- | --- | --- |\n"
        "| Better onboarding guidance | Reduce setup confusion | Improve activation |\n"
        "| More personalized reminders | Maintain habits | Boost retention |\n"
        "| Clearer premium comparison | Understand pricing | Improve conversion |\n\n"
        "## Anti-Features\n\n"
        "| Anti-feature | Why it hurts | What to avoid |\n"
        "| --- | --- | --- |\n"
        "| Noisy popups | Feels spammy | Avoid interruptive upsells |\n"
        "| Hidden billing detail | Erodes trust | Keep billing explicit |\n\n"
        "## Version Or Country Hotspots\n\n"
        "- Hotspot 1: JP reviews react strongly to typography and trust density.\n"
        "- Hotspot 2: BR reviews call out pricing and upgrade clarity.\n"
        "- Hotspot 3: US reviews emphasize time-to-value in onboarding.\n\n"
        "## Persona Or Segment Breakdowns\n\n"
        "| Segment | What they value | What they dislike |\n"
        "| --- | --- | --- |\n"
        "| New users | Guided setup | Complex first session |\n"
        "| Power users | Fast repeat actions | Slow or hidden controls |\n\n"
        "## Raw Data References\n\n"
        "- Review export: review-export.csv\n"
        "- Review insight report: review-insight-report.md\n"
        "- Sample review evidence file: review-quotes.md\n",
        encoding="utf-8",
    )

    (research_dir / "03-feature-opportunities.md").write_text(
        "# Feature Opportunities\n\n"
        f"- Initiative ID: `{initiative_id}`\n"
        "- Product: `Demo Product`\n"
        "- Research date: `2026-03-19`\n"
        "- Status: pending\n\n"
        "- Approved by:\n"
        "- Approved on:\n\n"
        "## Must-Have Features\n\n"
        "| Feature | Evidence | Why now |\n"
        "| --- | --- | --- |\n"
        "| Guided onboarding | Setup complaints | Improves activation |\n"
        "| Personalized home feed | Delight cluster | Drives repeat use |\n"
        "| Transparent premium framing | Pricing complaints | Improves conversion |\n"
        "| Trust and support surfaces | Support complaints | Protects quality |\n\n"
        "## Prioritized Capability Map\n\n"
        "| Capability | Priority | User value | Evidence |\n"
        "| --- | --- | --- | --- |\n"
        "| Guided onboarding | P0 | Faster time to value | Complaint cluster 1 |\n"
        "| Personalized feed | P0 | Daily relevance | Delight cluster 1 |\n"
        "| Reminder loop | P1 | Return habit | Feature request 2 |\n"
        "| Premium comparison | P1 | Better upgrade clarity | Feature request 3 |\n"
        "| Support and trust hub | P1 | Better recovery | Anti-feature 2 |\n\n"
        "## Differentiators\n\n"
        "| Differentiator | Why it matters | Proof |\n"
        "| --- | --- | --- |\n"
        "| Faster trusted onboarding | Reduces first-session drop | Complaint cluster 1 |\n"
        "| Better premium explanation | Converts without annoying users | Pricing review trend |\n\n"
        "## Avoidances\n\n"
        "| Avoidance | Why avoid it | Evidence |\n"
        "| --- | --- | --- |\n"
        "| Aggressive popup walls | Hurts trust | Anti-feature 1 |\n"
        "| Opaque billing copy | Triggers churn risk | Anti-feature 2 |\n\n"
        "## Open Hypotheses\n\n"
        "| Hypothesis | What to test | Success sign |\n"
        "| --- | --- | --- |\n"
        "| Personalized reminders lift retention | Reminder timing | Higher day-7 return |\n"
        "| Guided setup improves upgrade intent | First-session confidence | Higher activation-to-upgrade rate |\n\n"
        "## Scope Recommendation\n\n"
        "- Core outcomes: Fast activation, daily relevance, trusted conversion.\n"
        "- Why now: The market gap is clear around setup, trust, and value explanation.\n"
        "- Expansion outcomes: Social proof, collaborative loops, deeper recommendations.\n"
        "- Why later: These depend on a strong activation and retention base first.\n"
        "- Strategic bets: Personalized timing and trust-heavy premium framing.\n"
        "- Validation dependency: Confirm onboarding and premium copy in first launch.\n\n"
        "## Recommendation\n\n"
        "- Core feature set: Guided onboarding, personalized feed, reminder loop, premium comparison, support hub.\n"
        "- First premium lever: Personalized advanced insights.\n"
        "- Biggest UX risk: Overloading first session with decisions.\n"
        "- Biggest market risk: Weak differentiation versus established leaders.\n"
        "- Biggest retention lever: Useful repeat-use reminders and personalized feed quality.\n"
        "- Biggest trust or quality requirement: Transparent billing and visible support pathways.\n\n"
        "## Growth And Scale Recommendation\n\n"
        "- Primary growth loop: Personalized value drives sharing and return traffic.\n"
        "- Primary retention loop: Reminder + feed relevance reinforces daily return.\n"
        "- Main global expansion lever: Reusable onboarding and trust framework across locales.\n"
        "- Main operational constraint at scale: Content freshness and support responsiveness.\n"
        "- Why this can plausibly reach 10M DAU: Category demand, repeat use, and cross-market fit are all visible in competitor and review evidence.\n",
        encoding="utf-8",
    )


class SupernbCliIntegrationTests(unittest.TestCase):
    def test_prompt_bootstrap_auto_initializes_current_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "new-product"
            project_dir.mkdir(parents=True, exist_ok=True)

            proc = run_command(
                [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "supernb-prompt-bootstrap.py"),
                    "--project-dir",
                    str(project_dir),
                ]
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            initiative_specs = sorted((project_dir / ".supernb" / "initiatives").glob("*/initiative.yaml"))
            self.assertEqual(len(initiative_specs), 1)
            initiative_root = initiative_specs[0].parent
            self.assertTrue((initiative_root / "prompt-session.md").is_file())
            self.assertTrue((initiative_root / "prompt-report-template.json").is_file())
            run_status_json = initiative_root / "run-status.json"
            self.assertTrue(run_status_json.is_file())
            run_status = json.loads(run_status_json.read_text(encoding="utf-8"))
            self.assertEqual(run_status.get("selected_phase"), "research")

    def test_install_claude_code_user_global_writes_managed_global_claude_md(self) -> None:
        impeccable_dir = ROOT_DIR / ".supernb-cache" / "impeccable-dist" / "claude-code" / ".claude"
        if not impeccable_dir.is_dir():
            self.skipTest("built impeccable Claude Code bundle is not available in this checkout")

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_home = Path(tmp_dir) / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            bin_dir = Path(tmp_dir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            log_path = Path(tmp_dir) / "claude-install.log"
            write_fake_claude_for_install(bin_dir, log_path)

            env = os.environ.copy()
            env["HOME"] = str(temp_home)
            env["FAKE_CLAUDE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "install-claude-code.sh"), str(temp_home)],
                env=env,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            managed_claude_md = temp_home / ".claude" / "CLAUDE.md"
            self.assertTrue(managed_claude_md.is_file())
            managed_text = managed_claude_md.read_text(encoding="utf-8")
            self.assertIn("prompt-bootstrap --start-loop", managed_text)
            self.assertIn("use supernb", managed_text)
            self.assertIn("initiative-wide reassessment", managed_text)
            self.assertTrue((temp_home / ".claude" / "skills" / "supernb" / "SKILL.md").is_file())
            self.assertTrue((temp_home / ".claude" / "skills" / "impeccable" / "SKILL.md").is_file())

            logged_calls = log_path.read_text(encoding="utf-8")
            self.assertIn("plugin marketplace add", logged_calls)
            self.assertIn("bundles/claude-loop-marketplace", logged_calls)
            self.assertIn("plugin install supernb-loop@supernb --scope user", logged_calls)

    def test_install_claude_code_project_local_writes_managed_project_claude_md_with_prompt_examples(self) -> None:
        impeccable_dir = ROOT_DIR / ".supernb-cache" / "impeccable-dist" / "claude-code" / ".claude"
        if not impeccable_dir.is_dir():
            self.skipTest("built impeccable Claude Code bundle is not available in this checkout")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            temp_home = root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            project_dir = root / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            bin_dir = root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            log_path = root / "claude-install.log"
            write_fake_claude_for_install(bin_dir, log_path)

            env = os.environ.copy()
            env["HOME"] = str(temp_home)
            env["FAKE_CLAUDE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "install-claude-code.sh"), str(project_dir)],
                env=env,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            managed_claude_md = project_dir / "CLAUDE.md"
            self.assertTrue(managed_claude_md.is_file())
            managed_text = managed_claude_md.read_text(encoding="utf-8")
            self.assertIn("use supernb", managed_text)
            self.assertIn("use supernb to improve this project", managed_text)
            self.assertIn("使用 supernb", managed_text)
            self.assertIn("使用 supernb 对本项目进行完善和升级", managed_text)
            self.assertIn("用 supernb 完善这个项目", managed_text)
            self.assertIn("initiative-wide reassessment", managed_text)
            self.assertIn("prompt-bootstrap --start-loop --direct-bridge-fallback", managed_text)

    def test_verify_installs_accepts_supernb_loop_plugin_and_prompt_first_examples(self) -> None:
        impeccable_dir = ROOT_DIR / ".supernb-cache" / "impeccable-dist" / "claude-code" / ".claude"
        if not impeccable_dir.is_dir():
            self.skipTest("built impeccable Claude Code bundle is not available in this checkout")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            temp_home = root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            bin_dir = root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            log_path = root / "claude-install.log"
            write_fake_claude_for_prompt_first(bin_dir, log_path)

            env = os.environ.copy()
            env["HOME"] = str(temp_home)
            env["FAKE_CLAUDE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            install_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "install-claude-code.sh"), str(temp_home)],
                env=env,
            )
            self.assertEqual(install_proc.returncode, 0, install_proc.stderr or install_proc.stdout)

            verify_proc = run_command(
                [sys.executable, str(ROOT_DIR / "scripts" / "supernb-verify-installs.py"), "--harness", "claude-code"],
                env=env,
            )

            self.assertEqual(verify_proc.returncode, 0, verify_proc.stderr or verify_proc.stdout)
            self.assertIn("[PASS] claude-code (user)", verify_proc.stdout)
            self.assertIn("Claude Code plugin: supernb-loop@supernb (enabled)", verify_proc.stdout)

    def test_verify_installs_rejects_managed_claude_md_missing_reassessment_or_upgrade_examples(self) -> None:
        impeccable_dir = ROOT_DIR / ".supernb-cache" / "impeccable-dist" / "claude-code" / ".claude"
        if not impeccable_dir.is_dir():
            self.skipTest("built impeccable Claude Code bundle is not available in this checkout")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            temp_home = root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            bin_dir = root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            log_path = root / "claude-install.log"
            write_fake_claude_for_prompt_first(bin_dir, log_path)

            env = os.environ.copy()
            env["HOME"] = str(temp_home)
            env["FAKE_CLAUDE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

            install_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "install-claude-code.sh"), str(temp_home)],
                env=env,
            )
            self.assertEqual(install_proc.returncode, 0, install_proc.stderr or install_proc.stdout)

            managed_claude_md = temp_home / ".claude" / "CLAUDE.md"
            managed_text = managed_claude_md.read_text(encoding="utf-8")
            managed_text = managed_text.replace("- 使用 supernb 对本项目进行完善和升级\n", "")
            managed_text = managed_text.replace("- 用 supernb 完善这个项目\n", "")
            managed_text = managed_text.replace("4. Start with an initiative-wide reassessment. Compare the real repository state against research, PRD, design, planning, delivery, and release artifacts before deciding the work is only a current-phase patch.\n", "")
            managed_claude_md.write_text(managed_text, encoding="utf-8")

            verify_proc = run_command(
                [sys.executable, str(ROOT_DIR / "scripts" / "supernb-verify-installs.py"), "--harness", "claude-code"],
                env=env,
            )

            self.assertNotEqual(verify_proc.returncode, 0)
            self.assertIn("managed user instructions issue:", verify_proc.stdout)
            self.assertIn("initiative-wide reassessment", verify_proc.stdout)
            self.assertIn("完善和升级", verify_proc.stdout)

    def test_install_docs_and_scripts_do_not_hardcode_single_repo_owner(self) -> None:
        tracked_paths = [
            ROOT_DIR / "README.md",
            ROOT_DIR / "README.zh-CN.md",
            ROOT_DIR / "docs" / "platforms" / "claude-code.md",
            ROOT_DIR / "docs" / "platforms" / "codex.md",
            ROOT_DIR / "docs" / "platforms" / "opencode.md",
            ROOT_DIR / "docs" / "quickstart.md",
            ROOT_DIR / "docs" / "commands" / "claude-code.md",
            ROOT_DIR / "scripts" / "bootstrap-supernb.sh",
            ROOT_DIR / "scripts" / "install-claude-code-remote.sh",
            ROOT_DIR / ".codex" / "INSTALL.md",
            ROOT_DIR / ".opencode" / "INSTALL.md",
        ]

        for path in tracked_paths:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("raw.githubusercontent.com/WayJerry/supernb", text)
                self.assertNotIn("github.com/WayJerry/supernb.git", text)

    def test_prompt_first_smoke_flow_from_managed_claude_md_to_closeout_promise(self) -> None:
        impeccable_dir = ROOT_DIR / ".supernb-cache" / "impeccable-dist" / "claude-code" / ".claude"
        if not impeccable_dir.is_dir():
            self.skipTest("built impeccable Claude Code bundle is not available in this checkout")

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = write_spec(root)
            initiative_id = paths["initiative_root"].name
            write_planning_traceability_artifacts(paths, initiative_id)

            next_command = paths["initiative_root"] / "next-command.md"
            phase_packet = paths["initiative_root"] / "phase-packet.md"
            run_status = paths["initiative_root"] / "run-status.json"
            next_command.write_text("# Next Command\n\nPlan the next bounded batch.\n", encoding="utf-8")
            phase_packet.write_text("# Phase Packet\n\n- Planning is ready for bounded execution.\n", encoding="utf-8")
            run_status.write_text(
                json.dumps(
                    {
                        "initiative_id": initiative_id,
                        "selected_phase": "planning",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            temp_home = root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir(parents=True, exist_ok=True)
            log_path = root / "claude-install.log"
            write_fake_claude_for_prompt_first(fake_bin, log_path)

            env = dict(os.environ)
            env["HOME"] = str(temp_home)
            env["FAKE_CLAUDE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["CLAUDE_CODE_SESSION_ID"] = "session-prompt-first-smoke"

            install_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "install-claude-code.sh"), str(temp_home)],
                env=env,
            )
            self.assertEqual(install_proc.returncode, 0, install_proc.stderr or install_proc.stdout)

            managed_claude_md = temp_home / ".claude" / "CLAUDE.md"
            self.assertTrue(managed_claude_md.is_file())
            managed_text = managed_claude_md.read_text(encoding="utf-8")
            self.assertIn("prompt-bootstrap --start-loop --direct-bridge-fallback", managed_text)
            self.assertIn("initiative-wide reassessment", managed_text)

            bootstrap_proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-bootstrap",
                    "--spec",
                    str(paths["spec_path"]),
                    "--project-dir",
                    str(paths["project_dir"]),
                    "--no-run",
                    "--start-loop",
                ],
                cwd=paths["project_dir"],
                env=env,
            )
            self.assertEqual(bootstrap_proc.returncode, 0, bootstrap_proc.stderr or bootstrap_proc.stdout)
            self.assertIn("Ralph Loop started in current Claude session", bootstrap_proc.stdout)

            session_path = paths["initiative_root"] / "prompt-session.md"
            report_template = paths["initiative_root"] / "prompt-report-template.json"
            reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
            loop_manifest = paths["initiative_root"] / "ralph-loop-planning.json"
            audit_summary_path = paths["initiative_root"] / "ralph-loop-planning-audit.json"
            self.assertTrue(session_path.is_file())
            self.assertTrue(report_template.is_file())
            self.assertTrue(reassessment_path.is_file())
            self.assertTrue(loop_manifest.is_file())

            reassessment_text = reassessment_path.read_text(encoding="utf-8")
            self.assertIn("Initiative-Wide Reassessment", reassessment_text)
            self.assertIn("Earliest affected phase to reopen", reassessment_text)
            reassessment_path.write_text(
                reassessment_text.replace("- Status: pending", "- Status: completed")
                .replace("- Earliest affected phase to reopen:", "- Earliest affected phase to reopen: none")
                .replace(
                    "- Can the current selected phase continue without reopening upstream work: yes/no",
                    "- Can the current selected phase continue without reopening upstream work: yes",
                ),
                encoding="utf-8",
            )

            loop_manifest_payload = json.loads(loop_manifest.read_text(encoding="utf-8"))
            state_file = Path(loop_manifest_payload["state_file"])
            self.assertTrue(state_file.is_file())

            deadline = time.time() + 3
            while time.time() < deadline and not audit_summary_path.is_file():
                time.sleep(0.2)
            self.assertTrue(audit_summary_path.is_file())

            state_file.unlink()
            deadline = time.time() + 3
            audit_payload = None
            while time.time() < deadline:
                try:
                    audit_payload = json.loads(audit_summary_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    time.sleep(0.1)
                    continue
                if audit_payload.get("final_status") == "state_removed":
                    break
                time.sleep(0.2)
            self.assertIsNotNone(audit_payload)
            if audit_payload.get("final_status") != "state_removed":
                audit_payload = json.loads(audit_summary_path.read_text(encoding="utf-8"))
            self.assertEqual(audit_payload.get("final_status"), "state_removed")

            report_payload = json.loads(report_template.read_text(encoding="utf-8"))
            report_payload["summary"] = "Completed the bounded planning batch through the managed prompt-first workflow."
            report_payload["completed_items"] = [
                "Validated the planning traceability set.",
                "Prepared the planning batch for execution.",
            ]
            report_payload["remaining_items"] = []
            report_payload["artifacts_updated"] = [str((paths["plan_dir"] / "implementation-plan.md").resolve())]
            report_payload["commands_run"] = ["./scripts/supernb prompt-bootstrap --start-loop", "./scripts/supernb prompt-closeout"]
            report_payload["tests_run"] = ["npm test -- --runInBand", "npm run lint"]
            report_payload["validated_batches_completed"] = 1
            report_payload["batch_commits"] = ["abc123 plan: certify prompt-first planning batch"]
            report_payload["workflow_trace"] = {
                "brainstorming": {"used": False, "evidence": "Planning refinement did not need a separate brainstorming pass."},
                "writing_plans": {"used": True, "evidence": "Completed the implementation-plan planning batch and traceability update."},
                "test_driven_development": {"used": False, "evidence": "Planning closeout did not execute code changes."},
                "code_review": {"used": False, "evidence": "Planning closeout reviewed the plan artifact rather than code."},
                "using_git_worktrees": {"used": False, "evidence": "The smoke test stayed in one temporary workspace."},
                "subagent_or_executing_plans": {"used": True, "evidence": "Executed one bounded planning batch through prompt-first closeout."},
            }
            report_payload["loop_execution"] = {
                "used": True,
                "mode": "ralph-loop",
                "completion_promise": loop_manifest_payload["completion_promise"],
                "state_file": loop_manifest_payload["state_file"],
                "max_iterations": loop_manifest_payload["max_iterations"],
                "final_iteration": max(int(audit_payload.get("last_iteration", 0) or 0), 1),
                "exit_reason": "completion promise became true after managed prompt closeout",
                "evidence": str(audit_summary_path),
            }
            report_payload["recommended_result_status"] = "succeeded"
            report_payload["recommended_gate_action"] = "certify"
            report_payload["recommended_gate_status"] = "ready"
            report_payload["evidence_artifacts"] = [str(audit_summary_path)]
            report_template.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")

            closeout_proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-closeout",
                    "--spec",
                    str(paths["spec_path"]),
                    "--phase",
                    "planning",
                    "--report-json",
                    str(report_template),
                ],
                cwd=paths["project_dir"],
                env=env,
            )

            self.assertEqual(closeout_proc.returncode, 0, closeout_proc.stderr or closeout_proc.stdout)
            self.assertIn("Prompt closeout status: clean phase-complete", closeout_proc.stdout)
            self.assertIn("<promise>SUPERNB 2026-03-19-demo planning batch complete</promise>", closeout_proc.stdout)
            self.assertIn("Recorded result status: succeeded", closeout_proc.stdout)
            self.assertIn("Certification run: yes (apply)", closeout_proc.stdout)

    def test_prompt_closeout_blocks_when_initiative_reassessment_is_still_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            run_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(paths["spec_path"]),
            )
            self.assertEqual(run_proc.returncode, 0, msg=run_proc.stderr)

            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"])],
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
            self.assertTrue(reassessment_path.is_file())
            self.assertIn("- Status: pending", reassessment_path.read_text(encoding="utf-8"))

            closeout_proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-closeout",
                    "--spec",
                    str(paths["spec_path"]),
                ],
            )

            self.assertNotEqual(closeout_proc.returncode, 0)
            self.assertIn("initiative-wide reassessment", closeout_proc.stderr)
            self.assertIn("pending", closeout_proc.stderr)
            self.assertNotIn("Execution packet:", closeout_proc.stdout)

    def test_prompt_closeout_blocks_when_reassessment_requires_reopen_of_earlier_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            run_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(paths["spec_path"]),
            )
            self.assertEqual(run_proc.returncode, 0, msg=run_proc.stderr)

            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"])],
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
            reassessment_text = reassessment_path.read_text(encoding="utf-8")
            reassessment_path.write_text(
                reassessment_text.replace("- Status: pending", "- Status: completed")
                .replace("- Earliest affected phase to reopen:", "- Earliest affected phase to reopen: research")
                .replace(
                    "- Can the current selected phase continue without reopening upstream work: yes/no",
                    "- Can the current selected phase continue without reopening upstream work: no",
                ),
                encoding="utf-8",
            )

            closeout_proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-closeout",
                    "--spec",
                    str(paths["spec_path"]),
                ],
            )

            self.assertNotEqual(closeout_proc.returncode, 0)
            self.assertIn("cannot close out cleanly", closeout_proc.stderr)
            self.assertIn("prompt-bootstrap --spec", closeout_proc.stderr)
            self.assertIn("--phase research", closeout_proc.stderr)

    def test_prompt_sync_writes_session_contract_and_report_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            run_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(paths["spec_path"]),
            )
            self.assertEqual(run_proc.returncode, 0, msg=run_proc.stderr)

            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"])],
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            session_path = paths["initiative_root"] / "prompt-session.md"
            report_template = paths["initiative_root"] / "prompt-report-template.json"
            reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
            self.assertTrue(session_path.is_file())
            self.assertTrue(report_template.is_file())
            self.assertTrue(reassessment_path.is_file())

            session_text = session_path.read_text(encoding="utf-8")
            self.assertIn("Prompt Session Contract", session_text)
            self.assertIn("next-command.md", session_text)
            self.assertIn("prompt-closeout", session_text)
            self.assertIn("initiative-wide reassessment", session_text)
            self.assertIn("initiative-reassessment.md", session_text)

            reassessment_text = reassessment_path.read_text(encoding="utf-8")
            self.assertIn("Initiative-Wide Reassessment", reassessment_text)
            self.assertIn("Earliest affected phase to reopen", reassessment_text)

            template_payload = json.loads(report_template.read_text(encoding="utf-8"))
            self.assertIn("workflow_trace", template_payload)
            self.assertEqual(template_payload["recommended_result_status"], "needs-follow-up")

    def test_prompt_sync_non_loop_phase_matrix_writes_reassessment_contracts(self) -> None:
        phase_expectations = {
            "research": {"loop_required": False},
            "prd": {"loop_required": False},
            "design": {"loop_required": False},
            "release": {"loop_required": False},
        }

        for phase, expectation in phase_expectations.items():
            with self.subTest(phase=phase):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    paths = write_spec(Path(tmp_dir))
                    initiative_id = paths["initiative_root"].name
                    next_command = paths["initiative_root"] / "next-command.md"
                    phase_packet = paths["initiative_root"] / "phase-packet.md"
                    run_status = paths["initiative_root"] / "run-status.json"
                    next_command.write_text(f"# Next Command\n\n- Continue the {phase} phase.\n", encoding="utf-8")
                    phase_packet.write_text(f"# Phase Packet\n\n- {phase.title()} is ready.\n", encoding="utf-8")
                    run_status.write_text(
                        json.dumps(
                            {
                                "initiative_id": initiative_id,
                                "selected_phase": phase,
                                "next_command": {"path": str(next_command)},
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )

                    sync_proc = run_command(
                        ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"]), "--no-run"],
                    )
                    self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

                    session_path = paths["initiative_root"] / "prompt-session.md"
                    report_template = paths["initiative_root"] / "prompt-report-template.json"
                    reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
                    loop_manifest = paths["initiative_root"] / f"ralph-loop-{phase}.json"
                    self.assertTrue(session_path.is_file())
                    self.assertTrue(report_template.is_file())
                    self.assertTrue(reassessment_path.is_file())
                    self.assertTrue(loop_manifest.is_file())

                    session_text = session_path.read_text(encoding="utf-8")
                    reassessment_text = reassessment_path.read_text(encoding="utf-8")
                    loop_payload = json.loads(loop_manifest.read_text(encoding="utf-8"))
                    self.assertIn("initiative-wide reassessment", session_text)
                    self.assertIn("upgrade-artifacts", session_text)
                    self.assertIn("Initiative-Wide Reassessment", reassessment_text)
                    self.assertEqual(loop_payload.get("required"), expectation["loop_required"])
                    if expectation["loop_required"]:
                        self.assertIn("Ralph Loop Requirement", session_text)
                    else:
                        self.assertNotIn("Ralph Loop Requirement", session_text)

    def test_prompt_closeout_research_phase_records_without_promise_after_completed_reassessment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            initiative_id = paths["initiative_root"].name
            write_research_artifacts_for_certification(paths["project_dir"], initiative_id)
            run_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(paths["spec_path"]),
            )
            self.assertEqual(run_proc.returncode, 0, msg=run_proc.stderr)

            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"])],
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
            reassessment_text = reassessment_path.read_text(encoding="utf-8")
            reassessment_path.write_text(
                reassessment_text.replace("- Status: pending", "- Status: completed")
                .replace("- Earliest affected phase to reopen:", "- Earliest affected phase to reopen: none")
                .replace(
                    "- Can the current selected phase continue without reopening upstream work: yes/no",
                    "- Can the current selected phase continue without reopening upstream work: yes",
                ),
                encoding="utf-8",
            )

            report_template = paths["initiative_root"] / "prompt-report-template.json"
            write_report_json(report_template)

            closeout_proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-closeout",
                    "--spec",
                    str(paths["spec_path"]),
                    "--phase",
                    "research",
                    "--report-json",
                    str(report_template),
                ],
            )

            self.assertEqual(closeout_proc.returncode, 0, closeout_proc.stderr or closeout_proc.stdout)
            self.assertIn("Prompt closeout status: recorded", closeout_proc.stdout)
            self.assertNotIn("<promise>SUPERNB", closeout_proc.stdout)

    def test_prompt_sync_generates_ralph_loop_contract_for_delivery_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            initiative_id = paths["initiative_root"].name
            next_command = paths["initiative_root"] / "next-command.md"
            phase_packet = paths["initiative_root"] / "phase-packet.md"
            run_status = paths["initiative_root"] / "run-status.json"
            next_command.write_text("# Next Command\n\n- Execute the current delivery batch.\n", encoding="utf-8")
            phase_packet.write_text("# Phase Packet\n\n- Delivery is ready.\n", encoding="utf-8")
            run_status.write_text(
                json.dumps(
                    {
                        "initiative_id": initiative_id,
                        "selected_phase": "delivery",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"]), "--no-run"],
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            session_path = paths["initiative_root"] / "prompt-session.md"
            report_template = paths["initiative_root"] / "prompt-report-template.json"
            loop_prompt = paths["initiative_root"] / "ralph-loop-delivery.md"
            loop_manifest = paths["initiative_root"] / "ralph-loop-delivery.json"
            self.assertTrue(session_path.is_file())
            self.assertTrue(report_template.is_file())
            self.assertTrue(loop_prompt.is_file())
            self.assertTrue(loop_manifest.is_file())

            session_text = session_path.read_text(encoding="utf-8")
            self.assertIn("Ralph Loop Requirement", session_text)
            self.assertIn("setup-superpower-loop.sh", session_text)
            self.assertIn("prompt-closeout", session_text)
            self.assertIn("--apply-certification", session_text)

            loop_prompt_text = loop_prompt.read_text(encoding="utf-8")
            self.assertIn("stop-hook", loop_prompt_text)
            self.assertIn("Do not type the final promise manually.", loop_prompt_text)
            self.assertIn("prompt-closeout", loop_prompt_text)

            manifest_payload = json.loads(loop_manifest.read_text(encoding="utf-8"))
            self.assertEqual(manifest_payload["phase"], "delivery")
            self.assertTrue(manifest_payload["required"])
            self.assertTrue(manifest_payload["stop_hook_required"])
            self.assertIn("setup-superpower-loop.sh", manifest_payload["start_command_text"])

            template_payload = json.loads(report_template.read_text(encoding="utf-8"))
            self.assertTrue(template_payload["loop_execution"]["used"])
            self.assertEqual(template_payload["loop_execution"]["mode"], "ralph-loop")

    def test_prompt_sync_start_loop_creates_session_bound_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            initiative_id = paths["initiative_root"].name
            fake_bin = Path(tmp_dir) / "fake-bin"
            fake_bin.mkdir(parents=True, exist_ok=True)
            write_fake_claude(fake_bin)
            next_command = paths["initiative_root"] / "next-command.md"
            phase_packet = paths["initiative_root"] / "phase-packet.md"
            run_status = paths["initiative_root"] / "run-status.json"
            next_command.write_text("# Next Command\n\n- Execute the current delivery batch.\n", encoding="utf-8")
            phase_packet.write_text("# Phase Packet\n\n- Delivery is ready.\n", encoding="utf-8")
            run_status.write_text(
                json.dumps(
                    {
                        "initiative_id": initiative_id,
                        "selected_phase": "delivery",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            env = dict(os.environ)
            env["CLAUDE_CODE_SESSION_ID"] = "session-123"
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"]), "--no-run", "--start-loop"],
                env=env,
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            state_file = paths["project_dir"] / ".claude" / "superpower-loop-2026-03-19-demo-delivery.local.md"
            self.assertTrue(state_file.is_file())
            state_text = state_file.read_text(encoding="utf-8")
            self.assertIn("session_id: session-123", state_text)
            self.assertIn("completion_promise: \"SUPERNB 2026-03-19-demo delivery batch complete\"", state_text)

            audit_summary = paths["initiative_root"] / "ralph-loop-delivery-audit.json"
            audit_events = paths["initiative_root"] / "ralph-loop-delivery-audit.ndjson"
            deadline = time.time() + 3
            while time.time() < deadline and not audit_summary.is_file():
                time.sleep(0.2)
            self.assertTrue(audit_summary.is_file())
            self.assertTrue(audit_events.is_file())

            state_file.unlink()
            deadline = time.time() + 3
            while time.time() < deadline:
                payload = json.loads(audit_summary.read_text(encoding="utf-8"))
                if payload.get("final_status") == "state_removed":
                    break
                time.sleep(0.2)
            payload = json.loads(audit_summary.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("final_status"), "state_removed")
            self.assertEqual(payload.get("expected_session_id"), "session-123")

    def test_prompt_closeout_blocks_delivery_promise_when_certification_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            initiative_id = paths["initiative_root"].name
            next_command = paths["initiative_root"] / "next-command.md"
            phase_packet = paths["initiative_root"] / "phase-packet.md"
            run_status = paths["initiative_root"] / "run-status.json"
            next_command.write_text("# Next Command\n\n- Execute the current delivery batch.\n", encoding="utf-8")
            phase_packet.write_text("# Phase Packet\n\n- Delivery is ready.\n", encoding="utf-8")
            run_status.write_text(
                json.dumps(
                    {
                        "initiative_id": initiative_id,
                        "selected_phase": "delivery",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            sync_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"]), "--no-run"],
            )
            self.assertEqual(sync_proc.returncode, 0, msg=sync_proc.stderr)

            reassessment_path = paths["initiative_root"] / "initiative-reassessment.md"
            reassessment_text = reassessment_path.read_text(encoding="utf-8")
            reassessment_path.write_text(
                reassessment_text.replace("- Status: pending", "- Status: completed")
                .replace("- Earliest affected phase to reopen:", "- Earliest affected phase to reopen: none")
                .replace(
                    "- Can the current selected phase continue without reopening upstream work: yes/no",
                    "- Can the current selected phase continue without reopening upstream work: yes",
                ),
                encoding="utf-8",
            )

            report_template = paths["initiative_root"] / "prompt-report-template.json"
            payload = json.loads(report_template.read_text(encoding="utf-8"))
            payload["summary"] = "Tried to close out a delivery batch."
            payload["completed_items"] = ["Changed some code."]
            payload["evidence_artifacts"] = []
            payload["loop_execution"] = {
                "used": False,
                "mode": "none",
                "completion_promise": "",
                "state_file": "",
                "max_iterations": 0,
                "final_iteration": 0,
                "exit_reason": "",
                "evidence": "",
            }
            report_template.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            closeout_proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-closeout",
                    "--spec",
                    str(paths["spec_path"]),
                    "--phase",
                    "delivery",
                    "--report-json",
                    str(report_template),
                ]
            )

            self.assertNotEqual(closeout_proc.returncode, 0)
            self.assertNotIn("<promise>SUPERNB", closeout_proc.stdout)
            self.assertIn("Prompt closeout did not emit the Ralph Loop completion promise", closeout_proc.stderr)
            self.assertIn("Imported execution packet:", closeout_proc.stderr)
            self.assertIn("--certify", closeout_proc.stderr)
            self.assertNotIn("Traceback", closeout_proc.stderr)

    def test_prompt_sync_start_loop_requires_claude_session_id_with_actionable_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            initiative_id = paths["initiative_root"].name
            next_command = paths["initiative_root"] / "next-command.md"
            phase_packet = paths["initiative_root"] / "phase-packet.md"
            run_status = paths["initiative_root"] / "run-status.json"
            next_command.write_text("# Next Command\n\n- Execute the current delivery batch.\n", encoding="utf-8")
            phase_packet.write_text("# Phase Packet\n\n- Delivery is ready.\n", encoding="utf-8")
            run_status.write_text(
                json.dumps(
                    {
                        "initiative_id": initiative_id,
                        "selected_phase": "delivery",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "prompt-sync", "--spec", str(paths["spec_path"]), "--no-run", "--start-loop"],
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("CLAUDE_CODE_SESSION_ID is not set", proc.stderr)
            self.assertIn("active Claude Code session", proc.stderr)
            self.assertIn("If you only need the prompt files", proc.stderr)
            self.assertIn("--no-run", proc.stderr)

    def test_prompt_sync_start_loop_can_fallback_to_direct_claude_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            fake_bin = Path(tmp_dir) / "fake-bin"
            fake_bin.mkdir(parents=True, exist_ok=True)
            write_fake_claude(fake_bin)
            initiative_id = paths["initiative_root"].name
            next_command = paths["initiative_root"] / "next-command.md"
            phase_packet = paths["initiative_root"] / "phase-packet.md"
            run_status = paths["initiative_root"] / "run-status.json"
            next_command.write_text("# Next Command\n\nPlan the next bounded batch.\n", encoding="utf-8")
            phase_packet.write_text("# Phase Packet\n\n- Planning is ready.\n", encoding="utf-8")
            run_status.write_text(
                json.dumps(
                    {
                        "initiative_id": initiative_id,
                        "selected_phase": "planning",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["FAKE_CLAUDE_LOOP_DELETE_DELAY"] = "0.0"

            proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "supernb"),
                    "prompt-sync",
                    "--spec",
                    str(paths["spec_path"]),
                    "--no-run",
                    "--start-loop",
                    "--direct-bridge-fallback",
                ],
                env=env,
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("Direct bridge fallback activated", proc.stdout)
            self.assertIn("current Claude session must switch to observer mode", proc.stdout)
            self.assertIn("Do not continue editing or committing in parallel", proc.stdout)
            self.assertIn("direct bridge fallback was requested but prompt-sync is running with --no-run", proc.stdout.lower())
            self.assertIn("rerun prompt-sync without --no-run", proc.stdout.lower())
            packet_dirs = sorted(paths["executions_dir"].glob("*-planning-claude-code"))
            self.assertEqual(len(packet_dirs), 0)
            handoff_path = paths["initiative_root"] / "direct-bridge-handoff-planning.json"
            self.assertFalse(handoff_path.exists())

    def test_bootstrap_claude_code_defaults_to_user_global_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            temp_home = temp_root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            repo_dir = temp_root / "supernb-repo"
            scripts_dir = repo_dir / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            (repo_dir / ".git").mkdir()
            log_path = temp_root / "bootstrap.log"

            for name, body in {
                "update-supernb.sh": "#!/usr/bin/env bash\nexit 0\n",
                "update-upstreams.sh": "#!/usr/bin/env bash\nexit 0\n",
                "print-next-steps.sh": "#!/usr/bin/env bash\nexit 0\n",
                "install-claude-code.sh": "#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$SUPERNB_BOOTSTRAP_LOG\"\n",
            }.items():
                path = scripts_dir / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)

            env = dict(os.environ)
            env["HOME"] = str(temp_home)
            env["SUPERNB_BOOTSTRAP_LOG"] = str(log_path)

            proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "bootstrap-supernb.sh"),
                    "--repo-dir",
                    str(repo_dir),
                    "--harness",
                    "claude-code",
                    "--skip-update",
                ],
                env=env,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertEqual(log_path.read_text(encoding="utf-8").strip(), str(temp_home))

    def test_remote_claude_installer_defaults_to_user_global_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            temp_home = temp_root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            repo_dir = temp_root / "supernb-repo"
            clone_source = temp_root / "clone-source"
            scripts_dir = clone_source / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            log_path = temp_root / "remote-install.log"
            bin_dir = temp_root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)

            for name, body in {
                "update-supernb.sh": "#!/usr/bin/env bash\nexit 0\n",
                "update-upstreams.sh": "#!/usr/bin/env bash\nexit 0\n",
                "print-next-steps.sh": "#!/usr/bin/env bash\nexit 0\n",
                "install-claude-code.sh": "#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$SUPERNB_REMOTE_INSTALL_LOG\"\n",
            }.items():
                path = scripts_dir / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)

            write_fake_git_for_remote_install(bin_dir, clone_source)

            env = dict(os.environ)
            env["HOME"] = str(temp_home)
            env["SUPERNB_REMOTE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

            proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "install-claude-code-remote.sh"),
                    "--repo-url",
                    "https://github.com/Valiant-Cat/supernb.git",
                    "--repo-dir",
                    str(repo_dir),
                    "--skip-update",
                ],
                env=env,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertEqual(log_path.read_text(encoding="utf-8").strip(), str(temp_home))
            self.assertTrue((repo_dir / ".git").is_dir())

    def test_remote_claude_installer_accepts_project_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_root = Path(tmp_dir)
            temp_home = temp_root / "home"
            temp_home.mkdir(parents=True, exist_ok=True)
            project_dir = temp_root / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            repo_dir = temp_root / "supernb-repo"
            clone_source = temp_root / "clone-source"
            scripts_dir = clone_source / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            log_path = temp_root / "remote-install.log"
            bin_dir = temp_root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)

            for name, body in {
                "update-supernb.sh": "#!/usr/bin/env bash\nexit 0\n",
                "update-upstreams.sh": "#!/usr/bin/env bash\nexit 0\n",
                "print-next-steps.sh": "#!/usr/bin/env bash\nexit 0\n",
                "install-claude-code.sh": "#!/usr/bin/env bash\nprintf '%s\\n' \"$1\" >> \"$SUPERNB_REMOTE_INSTALL_LOG\"\n",
            }.items():
                path = scripts_dir / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)

            write_fake_git_for_remote_install(bin_dir, clone_source)

            env = dict(os.environ)
            env["HOME"] = str(temp_home)
            env["SUPERNB_REMOTE_INSTALL_LOG"] = str(log_path)
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

            proc = run_command(
                [
                    "bash",
                    str(ROOT_DIR / "scripts" / "install-claude-code-remote.sh"),
                    "--repo-url",
                    "https://github.com/Valiant-Cat/supernb.git",
                    "--repo-dir",
                    str(repo_dir),
                    "--project-dir",
                    str(project_dir),
                    "--skip-update",
                ],
                env=env,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
            self.assertEqual(log_path.read_text(encoding="utf-8").strip(), str(project_dir))

    def test_execute_next_claude_code_direct_auto_arms_ralph_loop_without_startup_race(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = write_spec(root)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir(parents=True, exist_ok=True)
            write_fake_claude(fake_bin)

            next_command = paths["initiative_root"] / "next-command.md"
            next_command.write_text("# Next Command\n\nPlan the next bounded batch.\n", encoding="utf-8")
            (paths["initiative_root"] / "run-status.json").write_text(
                json.dumps(
                    {
                        "initiative_id": paths["initiative_root"].name,
                        "selected_phase": "planning",
                        "next_command": {"path": str(next_command)},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["FAKE_CLAUDE_LOOP_DELETE_DELAY"] = "0.0"

            proc = run_command(
                [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "supernb-execute-next.py"),
                    "--spec",
                    str(paths["spec_path"]),
                    "--phase",
                    "planning",
                    "--harness",
                    "claude-code",
                    "--prompt-file",
                    str(next_command),
                ],
                env=env,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            packet_dirs = sorted(paths["executions_dir"].glob("*-planning-claude-code"))
            self.assertEqual(len(packet_dirs), 1)
            packet_dir = packet_dirs[0]

            request_payload = json.loads((packet_dir / "request.json").read_text(encoding="utf-8"))
            loop_contract = request_payload.get("ralph_loop") or {}
            self.assertTrue(loop_contract)
            self.assertEqual(request_payload.get("ralph_loop_plugin", {}).get("id"), "supernb-loop@supernb")
            self.assertEqual(request_payload.get("ralph_loop_plugin", {}).get("mode"), "session-local-plugin-dir")
            self.assertIn("--plugin-dir", request_payload.get("command", []))
            self.assertIn("--session-id", request_payload.get("command", []))
            self.assertEqual(
                loop_contract.get("plugin_dir"),
                str(ROOT_DIR / "bundles" / "claude-loop-marketplace" / "supernb-loop" / ".claude-plugin"),
            )

            audit_summary_path = packet_dir / "ralph-loop-audit.json"
            audit_summary = json.loads(audit_summary_path.read_text(encoding="utf-8"))
            self.assertEqual(audit_summary.get("final_status"), "state_removed")
            self.assertTrue(audit_summary.get("state_observed"))
            self.assertTrue(audit_summary.get("removed_after_observation"))
            self.assertEqual(audit_summary.get("expected_session_id"), loop_contract.get("session_id"))
            self.assertEqual(audit_summary.get("last_session_id"), loop_contract.get("session_id"))

            response_text = (packet_dir / "response.md").read_text(encoding="utf-8")
            self.assertIn("<promise>SUPERNB", response_text)

            suggestion = json.loads((packet_dir / "result-suggestion.json").read_text(encoding="utf-8"))
            self.assertFalse(any("Ralph Loop" in issue for issue in suggestion.get("workflow_issues", [])))

    def test_verify_claude_loop_detects_missing_second_iteration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            fake_bin = root / "fake-bin"
            fake_bin.mkdir(parents=True, exist_ok=True)
            write_fake_claude(fake_bin)

            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
            env["FAKE_CLAUDE_LOOP_DELETE_DELAY"] = "0.0"

            proc = run_command(
                [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "supernb-verify-claude-loop.py"),
                    "--allow-live-run",
                    "--workspace",
                    str(root / "verify-workspace"),
                    "--audit-timeout-seconds",
                    "3",
                ],
                env=env,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("last_iteration >= 2", proc.stderr)
            self.assertIn("Verification result:", proc.stderr)

    def test_debug_log_toggle_emits_initiative_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))

            enable_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "supernb"), "debug-log", "on", "--spec", str(paths["spec_path"])],
            )
            self.assertEqual(enable_proc.returncode, 0, msg=enable_proc.stderr)
            self.assertTrue((paths["project_dir"] / ".supernb" / "debug-logging.enabled").is_file())

            record_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-record-result.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--status",
                "blocked",
                "--summary",
                "Testing debug log capture",
                "--source",
                "manual-override",
                "--override-reason",
                "Need to inspect lifecycle logging",
                "--no-rerun",
            )
            self.assertEqual(record_proc.returncode, 0, msg=record_proc.stderr)

            debug_logs = sorted((paths["initiative_root"] / "debug-logs").glob("*.ndjson"))
            self.assertTrue(debug_logs)
            lines = [json.loads(line) for line in debug_logs[-1].read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(any(line["component"] == "supernb-record-result" and line["event"] == "start" for line in lines))
            self.assertTrue(any(line["component"] == "supernb-record-result" and line["event"] == "complete" for line in lines))

    def test_record_result_requires_override_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-record-result.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--status",
                "succeeded",
                "--summary",
                "Manual result",
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("--override-reason is required", proc.stderr)

    def test_record_result_rejects_gate_status_with_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-record-result.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "delivery",
                "--status",
                "verified",
                "--summary",
                "Wrong status kind",
                "--source",
                "manual-override",
                "--override-reason",
                "Testing validation guidance",
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("`verified` is a gate status, not a result status", proc.stderr)
            self.assertIn("succeeded, blocked, needs-follow-up, manual-follow-up, not-run, failed", proc.stderr)
            self.assertIn("certify-phase", proc.stderr)

    def test_import_execution_rejects_missing_evidence_before_packet_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            report_path = Path(tmp_dir) / "report.json"
            write_report_json(report_path, evidence_artifacts=["missing-proof.md"])

            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--report-json",
                str(report_path),
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("do not exist", proc.stderr)
            self.assertEqual(list(paths["executions_dir"].iterdir()), [])

    def test_import_and_apply_execution_records_packet_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            report_path = Path(tmp_dir) / "report.json"
            write_report_json(report_path)

            import_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--report-json",
                str(report_path),
            )
            self.assertEqual(import_proc.returncode, 0, msg=import_proc.stderr)

            packet_dirs = [path for path in paths["executions_dir"].iterdir() if path.is_dir()]
            self.assertEqual(len(packet_dirs), 1)

            apply_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-apply-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--packet",
                str(packet_dirs[0]),
                "--no-rerun",
            )
            self.assertEqual(apply_proc.returncode, 0, msg=apply_proc.stderr)

            result_files = list(paths["phase_results_dir"].glob("*.md"))
            self.assertEqual(len(result_files), 1)
            result_text = result_files[0].read_text(encoding="utf-8")
            self.assertIn("- Source: `execution-packet`", result_text)
            self.assertIn("- Source packet: `", result_text)

    def test_apply_execution_apply_certification_requires_succeeded_packet_with_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            report_path = Path(tmp_dir) / "report.json"
            write_report_json(report_path, recommended_result_status="needs-follow-up")

            import_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "research",
                "--report-json",
                str(report_path),
            )
            self.assertEqual(import_proc.returncode, 0, msg=import_proc.stderr)

            packet_dirs = [path for path in paths["executions_dir"].iterdir() if path.is_dir()]
            self.assertEqual(len(packet_dirs), 1)

            apply_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-apply-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--packet",
                str(packet_dirs[0]),
                "--apply-certification",
            )

            self.assertNotEqual(apply_proc.returncode, 0)
            self.assertIn("suggested_result_status=needs-follow-up", apply_proc.stderr)
            self.assertIn("--certify", apply_proc.stderr)
            self.assertIn("recorded first", apply_proc.stderr)

    def test_apply_execution_certify_failure_returns_clean_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            report_path = Path(tmp_dir) / "report.json"
            write_report_json(report_path, recommended_result_status="needs-follow-up")

            import_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--phase",
                "delivery",
                "--report-json",
                str(report_path),
            )
            self.assertEqual(import_proc.returncode, 0, msg=import_proc.stderr)

            packet_dirs = [path for path in paths["executions_dir"].iterdir() if path.is_dir()]
            self.assertEqual(len(packet_dirs), 1)

            apply_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-apply-execution.py"),
                "--spec",
                str(paths["spec_path"]),
                "--packet",
                str(packet_dirs[0]),
                "--certify",
                "--no-rerun",
            )

            self.assertNotEqual(apply_proc.returncode, 0)
            self.assertIn("Recorded phase result:", apply_proc.stdout)
            self.assertTrue(apply_proc.stderr.strip())
            self.assertNotIn("Traceback", apply_proc.stderr)

    def test_migrate_legacy_writes_mapping_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            paths = write_spec(root)
            legacy_root = root / "legacy-supernb"
            (legacy_root / "research").mkdir(parents=True, exist_ok=True)
            (legacy_root / "implementation").mkdir(parents=True, exist_ok=True)
            (legacy_root / "design").mkdir(parents=True, exist_ok=True)
            (legacy_root / "misc").mkdir(parents=True, exist_ok=True)
            (legacy_root / "research" / "market-research.md").write_text("# Market research\n", encoding="utf-8")
            (legacy_root / "implementation" / "IMPLEMENTATION-PLAN.md").write_text("# Legacy plan\n", encoding="utf-8")
            (legacy_root / "design" / "i18n-locale-notes.md").write_text("# Locale notes\n", encoding="utf-8")
            (legacy_root / "misc" / "random.md").write_text("# Ignore me\n", encoding="utf-8")

            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-migrate-legacy.py"),
                "--spec",
                str(paths["spec_path"]),
                "--legacy-root",
                str(legacy_root),
                "--no-upgrade",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            mapping_md = paths["initiative_root"] / "legacy-import" / "legacy-mapping.md"
            imported_misc = paths["initiative_root"] / "legacy-import" / "misc" / "random.md"
            self.assertTrue(mapping_md.is_file())
            self.assertFalse(imported_misc.exists())
            mapping_text = mapping_md.read_text(encoding="utf-8")
            self.assertIn("01-competitor-landscape.md", mapping_text)
            self.assertIn("implementation-plan.md", mapping_text)
            self.assertIn("i18n-strategy.md", mapping_text)

    def test_init_initiative_scaffold_uses_absolute_supernb_cli_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project_dir = root / "product"
            project_dir.mkdir(parents=True, exist_ok=True)

            env = dict(os.environ)
            env["PROJECT_DIR"] = str(project_dir)

            proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "init-initiative.sh"), "demo-cli-path", "Demo CLI Path"],
                env=env,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            spec_candidates = list((project_dir / ".supernb" / "initiatives").glob("*/initiative.yaml"))
            self.assertEqual(len(spec_candidates), 1)
            initiative_root = spec_candidates[0].parent
            expected_prefix = str((ROOT_DIR / "scripts" / "supernb").resolve())

            for artifact_name in ["run-status.md", "next-command.md", "phase-packet.md"]:
                artifact_text = (initiative_root / artifact_name).read_text(encoding="utf-8")
                self.assertIn(expected_prefix, artifact_text)
                self.assertNotIn("./scripts/supernb", artifact_text)

            self.assertIn(expected_prefix, proc.stdout)
            self.assertNotIn("Run ./scripts/supernb run", proc.stdout)

    def test_clean_initiative_archives_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = write_spec(Path(tmp_dir))
            brief = paths["command_briefs_dir"] / "20260319-120000-product-research.md"
            brief.write_text("# Brief\n", encoding="utf-8")

            proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-clean-initiative-artifacts.py"),
                "--spec",
                str(paths["spec_path"]),
                "--apply",
                "--keep-command-briefs",
                "0",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            archive_sessions = sorted((paths["initiative_root"] / "cleanup-archive").glob("session-*"))
            self.assertTrue(archive_sessions)
            manifest_md = archive_sessions[-1] / "cleanup-manifest.md"
            archived_brief = archive_sessions[-1] / "command-briefs" / brief.name
            self.assertFalse(brief.exists())
            self.assertTrue(archived_brief.is_file())
            self.assertTrue(manifest_md.is_file())

    def test_lifecycle_smoke_advances_from_research_to_prd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            project_dir = root / "product"
            project_dir.mkdir(parents=True, exist_ok=True)

            env = dict(os.environ)
            env.update(
                {
                    "PROJECT_DIR": str(project_dir),
                    "GOAL": "Build a research-backed 10M-DAU-grade product.",
                    "HARNESS": "claude-code",
                    "PLATFORM": "web",
                    "STACK": "react",
                    "PRODUCT_CATEGORY": "productivity",
                    "MARKETS": "US,JP,BR",
                    "RESEARCH_WINDOW": "last 90 days",
                    "SOURCE_LOCALE": "en",
                    "TARGET_LOCALES": "ja,pt-BR",
                }
            )

            init_proc = run_command(
                ["bash", str(ROOT_DIR / "scripts" / "init-initiative.sh"), "demo-lifecycle", "Demo Lifecycle"],
                env=env,
            )
            self.assertEqual(init_proc.returncode, 0, msg=init_proc.stderr)

            spec_candidates = list((project_dir / ".supernb" / "initiatives").glob("*/initiative.yaml"))
            self.assertEqual(len(spec_candidates), 1)
            spec_path = spec_candidates[0]
            initiative_id = spec_path.parent.name
            locator_path = ROOT_DIR / "artifacts" / "initiative-locations" / f"{initiative_id}.txt"
            self.addCleanup(lambda: locator_path.unlink(missing_ok=True))

            write_research_artifacts_for_certification(project_dir, initiative_id)

            run_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(spec_path),
            )
            self.assertEqual(run_proc.returncode, 0, msg=run_proc.stderr)

            report_path = root / "research-report.json"
            write_report_json(report_path)

            import_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-import-execution.py"),
                "--spec",
                str(spec_path),
                "--phase",
                "research",
                "--report-json",
                str(report_path),
            )
            self.assertEqual(import_proc.returncode, 0, msg=import_proc.stderr)

            packet_dirs = sorted((project_dir / ".supernb" / "initiatives" / initiative_id / "executions").glob("*-research-*"))
            self.assertEqual(len(packet_dirs), 1)

            apply_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-apply-execution.py"),
                "--spec",
                str(spec_path),
                "--packet",
                str(packet_dirs[0]),
                "--apply-certification",
                "--actor",
                "supernb-test",
            )
            self.assertEqual(apply_proc.returncode, 0, msg=apply_proc.stderr)

            rerun_proc = run_cli(
                str(ROOT_DIR / "scripts" / "supernb-run.py"),
                "--spec",
                str(spec_path),
            )
            self.assertEqual(rerun_proc.returncode, 0, msg=rerun_proc.stderr)

            run_status_json = project_dir / ".supernb" / "initiatives" / initiative_id / "run-status.json"
            run_status = json.loads(run_status_json.read_text(encoding="utf-8"))
            self.assertEqual(run_status.get("selected_phase"), "prd")
            self.assertEqual(run_status.get("phases", {}).get("research", {}).get("status"), "complete")

            certification_state = json.loads(
                (project_dir / ".supernb" / "initiatives" / initiative_id / "certification-state.json").read_text(encoding="utf-8")
            )
            self.assertTrue(certification_state["phases"]["research"]["passed"])


if __name__ == "__main__":
    unittest.main()
