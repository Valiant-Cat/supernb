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
- [single-capability-router.md](/Users/xiaomiao26_1_26/projects/supernb/commands/single-capability-router.md)
- [brainstorm-and-save.md](/Users/xiaomiao26_1_26/projects/supernb/commands/brainstorm-and-save.md)
- [ui-ux-upgrade.md](/Users/xiaomiao26_1_26/projects/supernb/commands/ui-ux-upgrade.md)
- [implementation-execution.md](/Users/xiaomiao26_1_26/projects/supernb/commands/implementation-execution.md)
- [i18n-localization-governance.md](/Users/xiaomiao26_1_26/projects/supernb/commands/i18n-localization-governance.md)

## Helpers

- `./scripts/show-command-template.sh <command>` prints the raw template
- `./scripts/render-command.sh --command <command> ...` renders a filled prompt
- `make show-command COMMAND=<command>` is the shortcut
- `make render-command COMMAND=<command> GOAL="..." ...` is the machine-fill shortcut

## Example

```text
Use supernb command: full-product-delivery
Goal: Build a commercial-grade personal finance product.
Context: Web + iOS, global launch, remote repo https://github.com/example/repo.git
Output: Research artifacts, PRD, UI/UX spec, implementation plan, validated code commits.
```
