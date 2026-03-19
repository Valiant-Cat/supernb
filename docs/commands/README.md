# Harness Command Mapping

This folder explains how to use `supernb` command templates across supported harnesses.

These docs do not assume that every harness has the same native command system.

The stable cross-harness base is:

- command templates live in `commands/`
- `./scripts/show-command-template.sh <command>` prints the template
- `./scripts/render-command.sh --command <command> ...` renders a filled command prompt
- `make show-command COMMAND=<command>` is the shortcut
- `make render-command COMMAND=<command> GOAL="..." ...` is the structured shortcut

Available harness guides:

- [claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/claude-code.md)
- [codex.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/codex.md)
- [opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/opencode.md)
