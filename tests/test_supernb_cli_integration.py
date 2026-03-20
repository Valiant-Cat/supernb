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
            plugin_id = os.environ.get("FAKE_CLAUDE_PLUGIN_ID", "superpowers@frad-dotclaude")
            plugin_status = os.environ.get("FAKE_CLAUDE_PLUGIN_STATUS", "enabled")

            if args[:2] == ["plugin", "list"]:
                print(plugin_id)
                print("  Version: 1.0.0")
                print("  Scope: User")
                print(f"  Status: {plugin_status}")
                sys.exit(0)

            if "-p" in args:
                prompt = sys.stdin.read()

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
                    time.sleep(0.8)
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


def write_report_json(path: Path, evidence_artifacts: list[str] | None = None) -> None:
    payload = {
        "completion_status": "completed",
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
        "recommended_result_status": "succeeded",
        "recommended_gate_action": "certify",
        "recommended_gate_status": "ready",
        "follow_up": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
            self.assertTrue(session_path.is_file())
            self.assertTrue(report_template.is_file())

            session_text = session_path.read_text(encoding="utf-8")
            self.assertIn("Prompt Session Contract", session_text)
            self.assertIn("next-command.md", session_text)
            self.assertIn("import-execution", session_text)

            template_payload = json.loads(report_template.read_text(encoding="utf-8"))
            self.assertIn("workflow_trace", template_payload)
            self.assertEqual(template_payload["recommended_result_status"], "needs-follow-up")

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

            loop_prompt_text = loop_prompt.read_text(encoding="utf-8")
            self.assertIn("<promise>SUPERNB", loop_prompt_text)
            self.assertIn("stop-hook", loop_prompt_text)

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

    def test_execute_next_claude_code_direct_auto_arms_ralph_loop(self) -> None:
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
            self.assertEqual(request_payload.get("ralph_loop_plugin", {}).get("id"), "superpowers@frad-dotclaude")
            self.assertEqual(request_payload.get("ralph_loop_plugin", {}).get("mode"), "session-local-plugin-dir")
            self.assertIn("--plugin-dir", request_payload.get("command", []))
            self.assertIn("--session-id", request_payload.get("command", []))
            self.assertEqual(loop_contract.get("plugin_dir"), str(ROOT_DIR / "upstreams" / "dotclaude" / "superpowers" / ".claude-plugin"))

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
