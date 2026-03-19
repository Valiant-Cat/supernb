# Harness Command Mapping

This folder explains how to use `supernb` command templates across supported harnesses.

These docs do not assume that every harness has the same native command system.

The stable cross-harness base is:

- command templates live in `commands/`
- `./scripts/supernb show-command <command>` prints the template
- `./scripts/supernb render-command --command <command> ...` renders a filled command prompt
- `./scripts/supernb save-command --command <command> ...` stores a dated command brief in `artifacts/commands/`
- `./scripts/supernb run --initiative-id <id>` reads `initiative.yaml`, computes gates, and writes the next command brief for the active phase
- `render-command.sh` validates that the command exists and now renders research-critical fields for product-definition flows
- `make show-command COMMAND=<command>` is the shortcut
- `make render-command COMMAND=<command> GOAL="..." ...` is the structured shortcut
- `make save-command COMMAND=<command> TITLE="..." GOAL="..." ...` is the archival shortcut

Available harness guides:

- [claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/claude-code.md)
- [codex.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/codex.md)
- [opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/opencode.md)
