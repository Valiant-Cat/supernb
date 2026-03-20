# supernb

[English](./README.md) | [简体中文](./README.zh-CN.md)

`supernb` is an orchestration layer that combines five capabilities into one product-building workflow:

- the latest `obra/superpowers` as the default planning and delivery engine
- bundled `supernb-loop@supernb` as the Ralph Loop enforcement layer for Claude Code prompt-first planning and delivery
- `impeccable` for UI/UX generation, critique, design-system definition, and post-implementation quality control
- bundled `sensortower-research` for competitor analysis, review mining, and evidence-backed PRD work
- bundled translation skills for localization extraction, key sync, and multi-language completion

The goal is not an MVP generator. The goal is a repeatable path from product idea to research-backed PRD, polished UI/UX, autonomous implementation, and 10M-DAU-grade commercial delivery.

`supernb` is framework-agnostic. Platform, stack, language, and repository choices are inputs from the user or project context, not fixed assumptions baked into the system.

`supernb` also treats localization as a first-class engineering rule: user-facing copy must not be hardcoded in code for app or web projects.

## What This Repository Is

This repository does not fork and rewrite the upstream projects. It acts as the coordination layer:

- `skills/` defines the `supernb` orchestration rules
- `bundles/` ships distributable local-only skills for one-pass installs
- `scripts/` keeps upstreams synced and prepares local installs
- `docs/` captures upstream analysis, architecture, and install guides
- `artifacts/` is the workspace for research, PRD, design, plan, and release outputs

It has two jobs:

- full-product delivery orchestration
- single-capability routing across all integrated upstream abilities
- reusable command entrypoints for predictable invocation
- initiative-spec-driven execution control

Its templates and artifact scaffolds are additive. They are meant to capture and organize outputs, not to replace or shrink the native documentation behavior of upstream `superpowers`.

## Distribution Model

`supernb` now uses two distribution paths:

- latest upstream repos are not vendored into git; bootstrap clones or fast-forwards them into `upstreams/`
- bundled local skills are committed under `bundles/skills/` so first-time users can install them in one pass

Installer behavior is idempotent by default:

- if a target skill or plugin is already installed, `supernb` skips it
- if it is missing, `supernb` provisions it automatically
- Claude Code default `superpowers` is auto-installed when missing
- OpenCode project `opencode.json` is auto-created or updated to include upstream `superpowers`

## Upstream Projects

As inspected locally on 2026-03-19:

- `obra/superpowers`
  - package version: `5.0.4`
  - provides a mature skills-based software delivery workflow
  - key strengths: brainstorming, plans, TDD, subagent-driven development, review, worktrees
- bundled `supernb-loop@supernb`
  - managed Claude Code loop plugin maintained in this repository
  - provides the stop-hook-backed Ralph Loop runtime used by prompt-first and direct Claude Code execution
- `pbakaus/impeccable`
  - package version: `1.5.1`
  - cross-provider design skill system with 20 commands and a provider build pipeline
- bundled `sensortower-research` skill
  - Python CLI wrapper around verified Sensor Tower endpoints plus review insight generation
- bundled translation skills
  - `flutter-l10n-translation` for ARB-based Flutter localization workflows
  - `android-i18n-translation` for `strings.xml` extraction and multi-locale translation

More detail: [docs/upstream-analysis.md](./docs/upstream-analysis.md)

## Workflow

`supernb` enforces a gated flow:

1. Research first. Run competitor lookup, reviews, and feature opportunity analysis before writing PRD.
2. PRD second. Every PRD must cite the research window and the competitor evidence used.
3. Design third. Use `impeccable` to define visual direction, design-system rules, key journey surfaces, and contrast/readability/interaction quality checks.
4. Implementation fourth. Use the latest `superpowers` to plan, write tests first, execute tasks, and verify outputs. For Claude Code prompt-first planning and delivery, use Ralph Loop so the agent cannot stop on self-judged completion.
5. Commit continuously. Every validated batch should be committed to git.

Architecture: [docs/architecture.md](./docs/architecture.md)

## Choose Your Platform

`supernb` now presents installation as three platform-native entrypoints instead of one bootstrap-first story.

### Claude Code

Best when you want prompt-first product delivery plus managed Ralph Loop enforcement.

Quick install:

```bash
./scripts/supernb build-impeccable
./scripts/supernb install-claude-code /path/to/your-project
```

Product page: [Supernb for Claude Code](./docs/platforms/claude-code.md)

### Codex

Best when you want native skill discovery and the cleanest full-stack `supernb` environment.

Quick install:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/WayJerry/supernb/refs/heads/main/.codex/INSTALL.md
```

Product page: [Supernb for Codex](./docs/platforms/codex.md)

### OpenCode

Best when you want project-local skills plus OpenCode-native plugin/config integration.

Quick install:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/WayJerry/supernb/refs/heads/main/.opencode/INSTALL.md
```

Product page: [Supernb for OpenCode](./docs/platforms/opencode.md)

New-user guide: [docs/quickstart.md](./docs/quickstart.md)

## Keys And Environment

`supernb` does not require a long list of keys just to start. Installation, orchestration, PRD, design, and delivery flows do not need extra credentials by default. You only need environment variables when you actually invoke the bundled skills that depend on external services.

Recommended rules:

- put keys in the shell environment that launches your harness, for example `~/.zshrc` or `~/.bashrc`
- after changing environment variables, restart Claude Code, Codex, or OpenCode so new sessions inherit them
- do not write real keys into the repository, `initiative.yaml`, command briefs, or commits

Common setup:

```bash
echo 'export SENSORTOWER_AUTH_TOKEN="st_your_token"' >> ~/.zshrc
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc
```

Or for the current shell only:

```bash
export SENSORTOWER_AUTH_TOKEN="st_your_token"
export OPENAI_API_KEY="sk-..."
```

Environment variables:

| Key | Used by | Required? | Recommended location | Notes |
| --- | --- | --- | --- | --- |
| `SENSORTOWER_AUTH_TOKEN` | `sensortower-research` primary API token | required only when using Sensor Tower research | `~/.zshrc` / `~/.bashrc` / shell that launches the harness | preferred canonical name |
| `SENSORTOWER_AUTH_TOKEN_BACKUP` | `sensortower-research` backup token | optional | same as above | used as fallback if the primary token is throttled or rejected |
| `SENSORTOWER_API_TOKEN` | `sensortower-research` compatibility alias | optional | same as above | usually unnecessary if `SENSORTOWER_AUTH_TOKEN` is set |
| `SENSOR_TOWER_API_TOKEN` | `sensortower-research` compatibility alias | optional | same as above | same as above |
| `SENSORTOWER_API_TOKEN_BACKUP` | `sensortower-research` backup compatibility alias | optional | same as above | same as above |
| `SENSOR_TOWER_API_TOKEN_BACKUP` | `sensortower-research` backup compatibility alias | optional | same as above | same as above |
| `OPENAI_API_KEY` | `flutter-l10n-translation`, `android-i18n-translation`, and related translation scripts in OpenAI mode | required only when using AI translation completion | `~/.zshrc` / `~/.bashrc` / shell that launches the harness | you can also pass `--api-key` to the scripts, but env vars are cleaner across harnesses |

Practical interpretation:

- if you only use `supernb` for orchestration, PRD, UI/UX, and code execution, you usually do not need extra keys
- if you use `sensortower-research`, configure at least one Sensor Tower token, preferably `SENSORTOWER_AUTH_TOKEN`
- if you use OpenAI-backed translation completion, configure `OPENAI_API_KEY`
- the `android-i18n-translation` `--provider google` path does not require an extra environment variable in this repo; only the OpenAI path needs `OPENAI_API_KEY`

Preferred standard names:

```bash
export SENSORTOWER_AUTH_TOKEN="st_your_token"
export OPENAI_API_KEY="sk-..."
```

These names align best with the bundled skills and CLI scripts.

## Install And Update

Use the platform pages for installation:

- Claude Code: [Supernb for Claude Code](./docs/platforms/claude-code.md)
- Codex: [Supernb for Codex](./docs/platforms/codex.md)
- OpenCode: [Supernb for OpenCode](./docs/platforms/opencode.md)

What the shared maintenance layer still does:

- syncs `superpowers` and `impeccable`
- installs bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation`
- skips already installed skills instead of overwriting them
- builds `impeccable` into an isolated local cache instead of mutating the upstream clone
- auto-installs the default Claude Code `superpowers` plugin when needed
- auto-ensures the OpenCode `superpowers` plugin entry in project config

Unified update path:

```bash
make update
```

That command:

- updates `supernb` itself when the current repo is clean and on its default branch
- safely skips self-update when your worktree is dirty or you are on a non-default branch
- updates `superpowers` and `impeccable`
- rebuilds `impeccable` by default
- writes JSON and Markdown update reports to `artifacts/updates/`

If you only want upstream caches:

```bash
make update-upstreams
```

If you already cloned this repo and want the old unified path, it still exists:

```bash
make bootstrap
```

Treat that as a compatibility shortcut, not the primary onboarding story.

Detailed install guides:

- Claude Code: [docs/platforms/claude-code.md](./docs/platforms/claude-code.md)
- Claude Code loop mode: [docs/install/claude-code-loop-mode.md](./docs/install/claude-code-loop-mode.md)
- Codex: [docs/platforms/codex.md](./docs/platforms/codex.md)
- OpenCode: [docs/platforms/opencode.md](./docs/platforms/opencode.md)

## Default And Optional Engines

- Default baseline for all supported harnesses: latest `obra/superpowers`
- Claude Code Ralph Loop enforcement layer for prompt-first planning and delivery: `supernb-loop@supernb`
- `execute-next` direct bridging is currently implemented for Codex and Claude Code. OpenCode remains a prepared-prompt/manual-handoff path.
- Do not install both `superpowers` plugins side by side in the same Claude Code environment. They share the same plugin name and overlapping skill names.
- In `supernb`, the Claude Code loop runtime is bundled and managed locally rather than depending on a separate upstream plugin repo.

## Initiative Control Plane

New initiative path:

```bash
./scripts/supernb init-initiative my-product "My Product"
./scripts/supernb run --initiative-id 2026-03-19-my-product
```

That flow:

- creates `.supernb/initiatives/<initiative-id>/initiative.yaml` in the active product workspace by default
- creates initiative-local `run-status.md` and `next-command.md`
- creates initiative-local `certification-state.json` as the phase certification source of truth
- creates initiative-local `phase-packet.md`, `run-log.md`, and archived `command-briefs/`
- creates initiative-local `phase-results/` for recorded execution outcomes
- creates initiative-local `executions/` packets for bridged harness runs
- creates per-execution `prompt-with-report.md`, `result-suggestion.md/json`, and `phase-readiness.md/json`
- computes which phase is blocked, ready, or complete
- generates the next structured command brief when the next phase is ready

For a new product initiative:

1. Run `./scripts/supernb init-initiative my-product "My Product"`.
2. Fill `.supernb/initiatives/<initiative-id>/initiative.yaml` in the product project.
3. Run `./scripts/supernb run --initiative-id <initiative-id>`.
   PRD, design, implementation plan, and release readiness now each carry traceability matrices with stable `Trace ID` rows. Certification blocks phase drift when those rows stop lining up.
   If you are using Claude Code by prompt rather than manually typing terminal commands, start with `./scripts/supernb prompt-bootstrap --initiative-id <initiative-id> --start-loop` once per work session so the agent gets a fresh session contract, report template, loop audit files, and an auto-started Ralph Loop for planning or delivery.
4. Execute the current phase with `./scripts/supernb execute-next --initiative-id <initiative-id> [--harness ... --project-dir ...]`.
   Direct Codex and Claude Code runs must return the structured `REPORT JSON` block; otherwise the packet is downgraded to `needs-follow-up` and cannot cleanly certify.
   For direct Claude Code planning or delivery runs, `execute-next` now auto-arms Ralph Loop, injects the bundled `supernb-loop` plugin through a session-local `--plugin-dir`, binds a generated Claude session id, waits until the audit watcher has observed the state file, and then writes packet-local audit files.
   `--dry-run` packets are preview-only and certification prefers the latest real non-dry-run packet.
   For OpenCode, this prepares the packet and prompt for manual execution rather than invoking the CLI directly.
5. Apply the execution packet with `./scripts/supernb apply-execution --initiative-id <initiative-id> --packet <execution-packet-dir> [--certify|--apply-certification]`.
6. For OpenCode or any manual handoff, import a structured execution result with `./scripts/supernb import-execution --initiative-id <initiative-id> --phase <phase> --report-json /path/to/report.json`, then apply that imported packet.
   `import-execution` now validates every declared `evidence_artifacts` path before it writes the packet.
7. Run `./scripts/supernb certify-phase --initiative-id <initiative-id> --phase <phase>` if you need an explicit standalone certification check.
8. Record the outcome manually with `./scripts/supernb record-result ...` only when you want to override the packet suggestion.
   Manual overrides now require `--override-reason`; packet-sourced results should continue to flow through `apply-execution`.
9. Apply the gate update with `./scripts/supernb advance-phase ...` only when you want to bypass the certification helper.
10. If you want initiative-scoped debug traces while testing on a real project, turn them on with `./scripts/supernb debug-log on --initiative-id <initiative-id>`.
    Debug events are written to `.supernb/initiatives/<initiative-id>/debug-logs/<YYYYMMDD>.ndjson` and stay enabled until you run `./scripts/supernb debug-log off ...` or override with `SUPERNB_DEBUG_LOG=0`.

For prompt-first sessions in Claude Code:

- say "use supernb" or "use supernb to improve this project"
- the managed `supernb` skill plus the managed user or project `CLAUDE.md` instructions should first run `./scripts/supernb prompt-bootstrap --start-loop` under the hood
- that bootstrap command should auto-discover the latest initiative in the current repo, or initialize one automatically if the repo has none yet
- the agent should read `.supernb/initiatives/<initiative-id>/prompt-session.md`
- for planning and delivery, that internal command should first verify the Claude Code loop plugin environment, then start the Ralph Loop and keep iterating until the completion promise is honestly true
- before ending the session, the agent should fill `.supernb/initiatives/<initiative-id>/prompt-report-template.json`, then run `./scripts/supernb prompt-closeout ...`
- for planning and delivery, `prompt-closeout` must succeed before the agent echoes the final `<promise>...</promise>` line

To prove that your local direct Claude CLI path really triggers the bundled Ralph Loop hook lifecycle, run:

```bash
./scripts/supernb verify-claude-loop --allow-live-run
```

That command performs a real `claude -p` smoke verification in a disposable workspace and only passes if the audit trail shows a genuine second loop iteration plus `state_removed`.

For an existing initiative created before the deeper templates and stricter gates were added:

1. Run `./scripts/supernb upgrade-artifacts --initiative-id <initiative-id>`.
2. Backfill the newly appended sections in the existing research, PRD, design, plan, and release Markdown artifacts.
3. Re-run `./scripts/supernb run --initiative-id <initiative-id>` and then certify the relevant phase again.

For a legacy loose `.supernb` project that predates initiatives entirely:

1. Create the new initiative first with `./scripts/supernb init-initiative ...`.
2. Run `./scripts/supernb migrate-legacy --initiative-id <initiative-id> [--legacy-root /path/to/.supernb]`.
3. Review `legacy-import/` plus `legacy-mapping.md`, reconcile the imported content into the initiative-scoped artifacts, then rerun `./scripts/supernb run`.

For housekeeping after many previews and retries:

- Run `./scripts/supernb clean-initiative --initiative-id <initiative-id>` to preview stale command briefs, dry-run packets, unsupported packets, and older execution artifacts.
- Re-run with `--apply` to archive the selected artifacts into a cleanup session with a manifest.
- Add `--delete` only when you explicitly want hard deletion instead of archival.
- Run `./scripts/supernb debug-log status --initiative-id <initiative-id>` to confirm whether persistent debug logging is enabled for the product project before a real-world smoke pass.

## Handy Commands

```bash
make update
make update-upstreams
make bootstrap
make install-claude-code PROJECT_DIR=/path/to/project
make verify-installs
make build-impeccable
make init-initiative INITIATIVE=my-product TITLE="My Product"
make run-initiative INITIATIVE_ID=2026-03-19-my-product
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=codex PROJECT_DIR=/path/to/repo DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet CERTIFY=1
make import-execution INITIATIVE_ID=2026-03-19-my-product PHASE=delivery REPORT_JSON=/path/to/report.json
make certify-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research
make upgrade-artifacts INITIATIVE_ID=2026-03-19-my-product
make migrate-legacy INITIATIVE_ID=2026-03-19-my-product LEGACY_ROOT=/path/to/.supernb
make clean-initiative INITIATIVE_ID=2026-03-19-my-product
make test
make record-result INITIATIVE_ID=2026-03-19-my-product STATUS=needs-follow-up SUMMARY="Manual override after audit" SOURCE=manual-override OVERRIDE_REASON="Packet evidence was incomplete"
make advance-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research STATUS=approved ACTOR="supernb"
make check-copy
make init-i18n STACK=web TARGET_LOCALES="zh-CN,ja"
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a 10M-DAU-grade finance app" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" QUALITY_BAR="10m-dau-grade" STACK="flutter"
make save-command COMMAND=full-product-delivery TITLE="10M DAU Finance App Brief" GOAL="Build a 10M-DAU-grade finance app" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" QUALITY_BAR="10m-dau-grade"
make install-codex
make install-claude-code
make install-opencode
```

Or use the scripts directly:

```bash
./scripts/supernb update-upstreams
./scripts/supernb update
./scripts/supernb bootstrap
./scripts/supernb install-claude-code /path/to/project
./scripts/supernb verify-installs --project-dir /path/to/project
./scripts/supernb build-impeccable
./scripts/supernb init-initiative my-product "My Product"
./scripts/supernb run --initiative-id 2026-03-19-my-product
./scripts/supernb execute-next --initiative-id 2026-03-19-my-product --harness codex --project-dir /path/to/repo --dry-run
./scripts/supernb apply-execution --initiative-id 2026-03-19-my-product --packet /path/to/packet --certify
./scripts/supernb import-execution --initiative-id 2026-03-19-my-product --phase delivery --report-json /path/to/report.json
./scripts/supernb certify-phase --initiative-id 2026-03-19-my-product --phase research
./scripts/supernb upgrade-artifacts --initiative-id 2026-03-19-my-product
./scripts/supernb migrate-legacy --initiative-id 2026-03-19-my-product --legacy-root /path/to/.supernb
./scripts/supernb clean-initiative --initiative-id 2026-03-19-my-product
./scripts/supernb test
./scripts/supernb record-result --initiative-id 2026-03-19-my-product --status needs-follow-up --summary "Manual override after audit" --source manual-override --override-reason "Packet evidence was incomplete"
./scripts/supernb advance-phase --initiative-id 2026-03-19-my-product --phase research --status approved --actor "supernb"
./scripts/supernb check-copy
./scripts/supernb init-i18n --stack web --target-dir . --target-locales "zh-CN,ja"
./scripts/supernb show-command full-product-delivery
./scripts/supernb render-command --command full-product-delivery --goal "Build a 10M-DAU-grade finance app" --product-category finance --markets SEA --research-window "last 90 days" --quality-bar "10m-dau-grade" --stack flutter
./scripts/supernb save-command --command full-product-delivery --title "10M DAU Finance App Brief" --goal "Build a 10M-DAU-grade finance app" --product-category finance --markets SEA --research-window "last 90 days" --quality-bar "10m-dau-grade"
```

## Repository Layout

```text
supernb/
├── artifacts/
│   ├── commands/
│   ├── design/
│   ├── initiatives/
│   ├── plans/
│   ├── prd/
│   ├── releases/
│   └── research/
├── bundles/
│   └── skills/
├── commands/
├── docs/
├── scripts/
├── skills/
└── upstreams/        # local cache, ignored by git
```

## More Documentation

Workflow guide: [docs/workflows/end-to-end.md](./docs/workflows/end-to-end.md)

Usage scenarios: [docs/usage-scenarios.md](./docs/usage-scenarios.md)

Capability matrix: [docs/capability-matrix.md](./docs/capability-matrix.md)

I18n guidance: [docs/i18n-stack-guidance.md](./docs/i18n-stack-guidance.md)

Initiative spec: [docs/initiative-spec.md](./docs/initiative-spec.md)

Command entrypoints: [commands/README.md](./commands/README.md)

Harness mapping: [docs/commands/README.md](./docs/commands/README.md)

## Notes

- bundled `sensortower-research` still expects a configured Sensor Tower token
- user-facing copy should be externalized into localization resources rather than hardcoded in code
- `impeccable` bundles are generated from source into `.supernb-cache/impeccable-dist` and are not committed here
- `upstreams/` is intentionally a local cache so `supernb` can track latest upstream code without vendoring entire repositories into git
