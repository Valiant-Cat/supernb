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

- [full-product-delivery.md](./full-product-delivery.md)
- [supernb-orchestrator.md](./supernb-orchestrator.md)
- [product-research.md](./product-research.md)
- [research-backed-prd.md](./research-backed-prd.md)
- [product-research-prd.md](./product-research-prd.md)
- [single-capability-router.md](./single-capability-router.md)
- [brainstorm-and-save.md](./brainstorm-and-save.md)
- [ui-ux-governance.md](./ui-ux-governance.md)
- [ui-ux-upgrade.md](./ui-ux-upgrade.md)
- [implementation-planning.md](./implementation-planning.md)
- [validated-delivery.md](./validated-delivery.md)
- [autonomous-delivery.md](./autonomous-delivery.md)
- [implementation-execution.md](./implementation-execution.md)
- [i18n-localization-governance.md](./i18n-localization-governance.md)

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
Goal: Build a 10M-DAU-grade personal finance product.
Context:
- repository: https://github.com/example/repo.git
- platform: Web + iOS
- product category: personal finance
- markets: global launch
- research window: last 90 days
Output: Research artifacts, PRD, UI/UX spec, implementation plan, validated code commits.
```
