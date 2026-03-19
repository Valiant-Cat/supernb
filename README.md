# supernb

`supernb` is an orchestration layer that combines four capabilities into one product-building workflow:

- `superpowers` for structured planning, task decomposition, and agent-driven implementation
- `superpowers@frad-dotclaude` for BDD-first execution and the Superpower Loop (`ralph-loop`)
- `impeccable` for UI/UX generation, critique, and post-implementation quality control
- `sensortower-research` for competitor analysis, review mining, and evidence-backed PRD work

The goal is not an MVP generator. The goal is a repeatable path from product idea to research-backed PRD, polished UI/UX, autonomous implementation, and commercial-grade delivery.

## What This Repository Is

This repository does not fork and rewrite the upstream projects. It acts as the coordination layer:

- `skills/` defines the `supernb` orchestration rules
- `scripts/` keeps upstreams synced and prepares local installs
- `docs/` captures upstream analysis, architecture, and install guides
- `artifacts/` is the workspace for research, PRD, design, plan, and release outputs

## Upstream Projects

As inspected locally on 2026-03-19:

- `obra/superpowers`
  - package version: `5.0.4`
  - provides a mature skills-based software delivery workflow
  - key strengths: brainstorming, plans, TDD, subagent-driven development, review, worktrees
- `FradSer/dotclaude`
  - relevant plugin: `superpowers` version `2.0.0`
  - key addition: BDD-oriented execution plus Superpower Loop state/hook automation
  - `ralph-loop` is not a separate repo here; it is the loop machinery in `scripts/setup-superpower-loop.sh` and `hooks/stop-hook.sh`
- `pbakaus/impeccable`
  - package version: `1.5.1`
  - cross-provider design skill system with 20 commands and a provider build pipeline
- local `sensortower-research` skill
  - Python CLI wrapper around verified Sensor Tower endpoints plus review insight generation

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
   Use `superpowers + ralph-loop` to plan, write tests first, execute tasks, and keep iterating until verified.
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
- Codex: [docs/install/codex.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/codex.md)
- OpenCode: [docs/install/opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/opencode.md)

## Handy Commands

```bash
make update
make build-impeccable
make install-codex
make install-claude-code
make install-opencode
```

Or use the scripts directly:

```bash
./scripts/update-upstreams.sh
./scripts/build-impeccable-dist.sh
./scripts/install-codex.sh
```

## Repository Layout

```text
supernb/
├── artifacts/
│   ├── design/
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

1. Start with the `product-research-prd` skill.
2. Move to `ui-ux-governance` only after the PRD is evidence-backed.
3. Use `autonomous-delivery` after design approval.
4. Keep `supernb-orchestrator` active when the goal is end-to-end product delivery.

## Notes

- `sensortower-research` expects a configured Sensor Tower token.
- `impeccable` bundles are generated from source and are not committed here.
- `upstreams/` is intentionally a local cache so `supernb` can track latest upstream code without vendoring entire repositories into git.

