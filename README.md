# supernb

`supernb` is an orchestration layer that combines five capabilities into one product-building workflow:

- the latest `obra/superpowers` as the default planning and delivery engine
- `superpowers@frad-dotclaude` as an optional Claude Code loop executor for bounded long-running tasks
- `impeccable` for UI/UX generation, critique, and post-implementation quality control
- `sensortower-research` for competitor analysis, review mining, and evidence-backed PRD work
- local translation skills for localization extraction, key sync, and multi-language completion

The goal is not an MVP generator. The goal is a repeatable path from product idea to research-backed PRD, polished UI/UX, autonomous implementation, and commercial-grade delivery.

`supernb` is framework-agnostic. Platform, stack, language, and repository choices are inputs from the user or project context, not fixed assumptions baked into the system.

`supernb` also treats localization as a first-class engineering rule: user-facing copy must not be hardcoded in code for app or web projects.

## What This Repository Is

This repository does not fork and rewrite the upstream projects. It acts as the coordination layer:

- `skills/` defines the `supernb` orchestration rules
- `scripts/` keeps upstreams synced and prepares local installs
- `docs/` captures upstream analysis, architecture, and install guides
- `artifacts/` is the workspace for research, PRD, design, plan, and release outputs

It has two jobs:

- full-product delivery orchestration
- single-capability routing across all integrated upstream abilities

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
- local `sensortower-research` skill
  - Python CLI wrapper around verified Sensor Tower endpoints plus review insight generation
- local translation skills
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

Clone this repo and then run:

```bash
make update
```

That will:

- clone or fast-forward `superpowers`, `dotclaude`, and `impeccable` into `upstreams/`
- build `impeccable` provider bundles if Bun is available

Then install for the harness you use:

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
make build-impeccable
make init-initiative INITIATIVE=my-product TITLE="My Product"
make install-codex
make install-claude-code
make install-opencode
```

Or use the scripts directly:

```bash
./scripts/update-upstreams.sh
./scripts/build-impeccable-dist.sh
./scripts/init-initiative.sh my-product "My Product"
./scripts/install-codex.sh
```

## Repository Layout

```text
supernb/
├── artifacts/
│   ├── design/
│   ├── initiatives/
│   ├── plans/
│   ├── prd/
│   ├── releases/
│   └── research/
├── docs/
├── scripts/
├── skills/
└── upstreams/        # local cache, ignored by git
```

## Recommended Usage

For a new product initiative:

1. Run `make init-initiative INITIATIVE=my-product TITLE="My Product"`.
2. Start with the `product-research-prd` skill and fill the research templates.
3. Move to `ui-ux-governance` only after the PRD is evidence-backed.
4. Use `autonomous-delivery` after design approval.
5. Keep `supernb-orchestrator` active when the goal is end-to-end product delivery.

Workflow guide: [docs/workflows/end-to-end.md](/Users/xiaomiao26_1_26/projects/supernb/docs/workflows/end-to-end.md)
Usage scenarios: [docs/usage-scenarios.md](/Users/xiaomiao26_1_26/projects/supernb/docs/usage-scenarios.md)
Capability matrix: [docs/capability-matrix.md](/Users/xiaomiao26_1_26/projects/supernb/docs/capability-matrix.md)

## Notes

- `sensortower-research` expects a configured Sensor Tower token.
- User-facing copy should be externalized into localization resources rather than hardcoded in code.
- `impeccable` bundles are generated from source and are not committed here.
- `upstreams/` is intentionally a local cache so `supernb` can track latest upstream code without vendoring entire repositories into git.
