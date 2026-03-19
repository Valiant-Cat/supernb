# Command Entrypoints

These command entrypoints give `supernb` a fixed invocation format.

Use them as stable prompt templates in Claude Code, Codex, OpenCode, or other harnesses.

## Format

```text
Use supernb command: <command-name>
Goal: <what you want>
Context: <repo, stack, constraints, market, etc.>
Output: <what should be saved, implemented, or returned>
```

## Available Commands

- [full-product-delivery.md](/Users/xiaomiao26_1_26/projects/supernb/commands/full-product-delivery.md)
- [supernb-orchestrator.md](/Users/xiaomiao26_1_26/projects/supernb/commands/supernb-orchestrator.md)
- [product-research-prd.md](/Users/xiaomiao26_1_26/projects/supernb/commands/product-research-prd.md)
- [single-capability-router.md](/Users/xiaomiao26_1_26/projects/supernb/commands/single-capability-router.md)
- [brainstorm-and-save.md](/Users/xiaomiao26_1_26/projects/supernb/commands/brainstorm-and-save.md)
- [ui-ux-governance.md](/Users/xiaomiao26_1_26/projects/supernb/commands/ui-ux-governance.md)
- [ui-ux-upgrade.md](/Users/xiaomiao26_1_26/projects/supernb/commands/ui-ux-upgrade.md)
- [autonomous-delivery.md](/Users/xiaomiao26_1_26/projects/supernb/commands/autonomous-delivery.md)
- [implementation-execution.md](/Users/xiaomiao26_1_26/projects/supernb/commands/implementation-execution.md)
- [i18n-localization-governance.md](/Users/xiaomiao26_1_26/projects/supernb/commands/i18n-localization-governance.md)

## Helpers

- `./scripts/show-command-template.sh <command>` prints the raw template
- `./scripts/render-command.sh --command <command> ...` renders a filled prompt
- `./scripts/save-command-brief.sh --command <command> ...` saves a dated brief into `artifacts/commands/`
- `make show-command COMMAND=<command>` is the shortcut
- `make render-command COMMAND=<command> GOAL="..." ...` is the machine-fill shortcut
- `make save-command COMMAND=<command> TITLE="..." GOAL="..." ...` is the archival shortcut

## Example

```text
Use supernb command: full-product-delivery
Goal: Build a commercial-grade personal finance product.
Context:
- repository: https://github.com/example/repo.git
- platform: Web + iOS
- product category: personal finance
- markets: global launch
- research window: last 90 days
Output: Research artifacts, PRD, UI/UX spec, implementation plan, validated code commits.
```
