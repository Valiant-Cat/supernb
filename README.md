# supernb

`supernb` is an orchestration layer that combines five capabilities into one product-building workflow:

- the latest `obra/superpowers` as the default planning and delivery engine
- `superpowers@frad-dotclaude` as an optional Claude Code loop executor for bounded long-running tasks
- `impeccable` for UI/UX generation, critique, and post-implementation quality control
- bundled `sensortower-research` for competitor analysis, review mining, and evidence-backed PRD work
- bundled translation skills for localization extraction, key sync, and multi-language completion

The goal is not an MVP generator. The goal is a repeatable path from product idea to research-backed PRD, polished UI/UX, autonomous implementation, and commercial-grade delivery.

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
  - package version: `5.0.5`
  - provides a mature skills-based software delivery workflow
  - key strengths: brainstorming, plans, TDD, subagent-driven development, review, worktrees
- `FradSer/dotclaude`
  - relevant plugin: `superpowers` version `2.0.0`
  - key addition: BDD-oriented execution plus optional Superpower Loop state/hook automation
  - `ralph-loop` is not a separate repo here; it is the loop machinery in `scripts/setup-superpower-loop.sh` and `hooks/stop-hook.sh`
- `pbakaus/impeccable`
  - package version: `1.5.1`
  - cross-provider design skill system with 20 commands and a provider build pipeline
- bundled `sensortower-research` skill
  - Python CLI wrapper around verified Sensor Tower endpoints plus review insight generation
- bundled translation skills
  - `flutter-l10n-translation` for ARB-based Flutter localization workflows
  - `android-i18n-translation` for `strings.xml` extraction and multi-locale translation

More detail: [docs/upstream-analysis.md](/Users/xiaomiao26_1_26/projects/supernb/docs/upstream-analysis.md)

## supernb Workflow

`supernb` enforces a gated flow:

1. Research first.
   Run competitor lookup, reviews, and feature opportunity analysis before writing PRD.
2. PRD second.
   Every PRD must cite the research window and the competitor evidence used.
3. Design third.
   Use `impeccable` to define visual direction, page-level UI/UX, and contrast/readability checks.
4. Implementation fourth.
   Use the latest `superpowers` to plan, write tests first, execute tasks, and verify outputs.
   Use the Frad loop only when a Claude Code task genuinely benefits from bounded persistence.
5. Commit continuously.
   Every validated batch should be committed to git.

Architecture: [docs/architecture.md](/Users/xiaomiao26_1_26/projects/supernb/docs/architecture.md)

## Quick Start

Fastest path:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh)
```

If auto-detection is ambiguous:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness codex
```

Then use one of the three main command entrypoints:

```bash
./scripts/supernb show-command full-product-delivery
./scripts/supernb render-command --command full-product-delivery --goal "Build a commercial-grade product" --product-category "finance" --markets "SEA" --research-window "last 90 days" --stack "your stack"
./scripts/supernb save-command --command full-product-delivery --title "Delivery Brief" --goal "Build a commercial-grade product" --product-category "finance" --markets "SEA" --research-window "last 90 days" --stack "your stack"
```

New-user guide: [docs/quickstart.md](/Users/xiaomiao26_1_26/projects/supernb/docs/quickstart.md)

What bootstrap now does:

- syncs `superpowers`, `dotclaude`, and `impeccable`
- installs bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation`
- skips already installed skills instead of overwriting them
- builds `impeccable` into an isolated local cache instead of mutating the upstream clone
- auto-installs the default Claude Code `superpowers` plugin when needed
- auto-ensures the OpenCode `superpowers` plugin entry in project config

New initiative control-plane path:

```bash
./scripts/supernb init-initiative my-product "My Product"
./scripts/supernb run --initiative-id 2026-03-19-my-product
```

That flow now:

- creates `artifacts/initiatives/<initiative-id>/initiative.yaml`
- creates initiative-local `run-status.md` and `next-command.md`
- creates initiative-local `phase-packet.md`, `run-log.md`, and archived `command-briefs/`
- creates initiative-local `phase-results/` for recorded execution outcomes
- creates initiative-local `executions/` packets for bridged harness runs
- creates per-execution `prompt-with-report.md`, `result-suggestion.md/json`, and `phase-readiness.md/json` so packet outcomes can be applied safely with completed items, remaining items, evidence, and phase-specific readiness checks
- computes which phase is blocked, ready, or complete
- generates the next structured command brief when the next phase is ready

Unified update path:

```bash
make update
```

That command now:

- updates `supernb` itself when the current repo is clean and on its default branch
- safely skips self-update when your worktree is dirty or you are on a non-default branch
- updates `superpowers`, `dotclaude`, and `impeccable`
- rebuilds `impeccable` by default
- writes JSON and Markdown update reports to `artifacts/updates/`

If you only want upstream caches:

```bash
make update-upstreams
```

If you already cloned this repo:

```bash
make bootstrap
```

If you need explicit harness/project selection:

```bash
make bootstrap HARNESS=claude-code PROJECT_DIR=/path/to/project
make bootstrap HARNESS=opencode PROJECT_DIR=/path/to/project
make bootstrap HARNESS=codex
```

Detailed install guides:

- Claude Code: [docs/install/claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/claude-code.md)
- Claude Code loop mode: [docs/install/claude-code-loop-mode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/claude-code-loop-mode.md)
- Codex: [docs/install/codex.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/codex.md)
- OpenCode: [docs/install/opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/opencode.md)

## Default And Optional Engines

- Default baseline for all supported harnesses: latest `obra/superpowers`
- Optional Claude Code-only enhancer: `superpowers@frad-dotclaude`
- Do not install both `superpowers` plugins side by side in the same Claude Code environment. They share the same plugin name and overlapping skill names.
- In `supernb`, `dotclaude` is treated as an execution add-on, not the primary workflow base.

## Handy Commands

```bash
make update
make update-upstreams
make bootstrap
make build-impeccable
make init-initiative INITIATIVE=my-product TITLE="My Product"
make run-initiative INITIATIVE_ID=2026-03-19-my-product
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=codex PROJECT_DIR=/path/to/repo DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet CERTIFY=1
make certify-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research
make record-result INITIATIVE_ID=2026-03-19-my-product STATUS=succeeded SUMMARY="Research batch finished"
make advance-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research STATUS=approved ACTOR="supernb"
make check-copy
make init-i18n STACK=web TARGET_LOCALES="zh-CN,ja"
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a finance app" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" QUALITY_BAR="commercial-grade" STACK="flutter"
make save-command COMMAND=full-product-delivery TITLE="Finance App Brief" GOAL="Build a finance app" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" QUALITY_BAR="commercial-grade"
make install-codex
make install-claude-code
make install-opencode
```

Or use the scripts directly:

```bash
./scripts/supernb update-upstreams
./scripts/supernb update
./scripts/supernb bootstrap
./scripts/supernb build-impeccable
./scripts/supernb init-initiative my-product "My Product"
./scripts/supernb run --initiative-id 2026-03-19-my-product
./scripts/supernb execute-next --initiative-id 2026-03-19-my-product --harness codex --project-dir /path/to/repo --dry-run
./scripts/supernb apply-execution --initiative-id 2026-03-19-my-product --packet /path/to/packet --certify
./scripts/supernb certify-phase --initiative-id 2026-03-19-my-product --phase research
./scripts/supernb record-result --initiative-id 2026-03-19-my-product --status succeeded --summary "Research batch finished"
./scripts/supernb advance-phase --initiative-id 2026-03-19-my-product --phase research --status approved --actor "supernb"
./scripts/supernb check-copy
./scripts/supernb init-i18n --stack web --target-dir . --target-locales "zh-CN,ja"
./scripts/supernb show-command full-product-delivery
./scripts/supernb render-command --command full-product-delivery --goal "Build a finance app" --product-category finance --markets SEA --research-window "last 90 days" --quality-bar "commercial-grade" --stack flutter
./scripts/supernb save-command --command full-product-delivery --title "Finance App Brief" --goal "Build a finance app" --product-category finance --markets SEA --research-window "last 90 days" --quality-bar "commercial-grade"
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

## Recommended Usage

For a new product initiative:

1. Run `./scripts/supernb init-initiative my-product "My Product"`.
2. Fill `artifacts/initiatives/<initiative-id>/initiative.yaml`.
3. Run `./scripts/supernb run --initiative-id <initiative-id>`.
4. Execute the current phase with `./scripts/supernb execute-next --initiative-id <initiative-id> [--harness ... --project-dir ...]`.
5. Apply the execution packet with `./scripts/supernb apply-execution --initiative-id <initiative-id> --packet <execution-packet-dir> [--certify|--apply-certification]`.
6. Run `./scripts/supernb certify-phase --initiative-id <initiative-id> --phase <phase>` if you need an explicit standalone certification check.
7. Record the outcome manually with `./scripts/supernb record-result ...` only when you want to override the packet suggestion.
8. Apply the gate update with `./scripts/supernb advance-phase ...` only when you want to bypass the certification helper.

Workflow guide: [docs/workflows/end-to-end.md](/Users/xiaomiao26_1_26/projects/supernb/docs/workflows/end-to-end.md)
Usage scenarios: [docs/usage-scenarios.md](/Users/xiaomiao26_1_26/projects/supernb/docs/usage-scenarios.md)
Capability matrix: [docs/capability-matrix.md](/Users/xiaomiao26_1_26/projects/supernb/docs/capability-matrix.md)
I18n guidance: [docs/i18n-stack-guidance.md](/Users/xiaomiao26_1_26/projects/supernb/docs/i18n-stack-guidance.md)
Initiative spec: [docs/initiative-spec.md](/Users/xiaomiao26_1_26/projects/supernb/docs/initiative-spec.md)
Command entrypoints: [commands/README.md](/Users/xiaomiao26_1_26/projects/supernb/commands/README.md)
Harness mapping: [docs/commands/README.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/README.md)

## Notes

- bundled `sensortower-research` still expects a configured Sensor Tower token.
- User-facing copy should be externalized into localization resources rather than hardcoded in code.
- `impeccable` bundles are generated from source into `.supernb-cache/impeccable-dist` and are not committed here.
- `upstreams/` is intentionally a local cache so `supernb` can track latest upstream code without vendoring entire repositories into git.
