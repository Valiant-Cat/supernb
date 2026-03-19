# Harness Command Mapping

This folder explains how to use `supernb` command templates across supported harnesses.

These docs do not assume that every harness has the same native command system.

The stable cross-harness base is:

- command templates live in `commands/`
- `./scripts/supernb show-command <command>` prints the template
- `./scripts/supernb render-command --command <command> ...` renders a filled command prompt
- `./scripts/supernb save-command --command <command> ...` stores a dated command brief in `artifacts/commands/`
- `./scripts/supernb run --initiative-id <id>` reads `initiative.yaml`, computes gates, and writes the next command brief for the active phase
- `./scripts/supernb execute-next --initiative-id <id> [--harness ...]` bridges the current `next-command.md` into a supported harness CLI and records an execution packet
- `./scripts/supernb import-execution --initiative-id <id> --phase <phase> --report-json <file>` turns a manual or OpenCode run into a normal execution packet and fails early if declared evidence paths do not resolve
- `./scripts/supernb apply-execution --initiative-id <id> --packet <dir>` converts an execution packet into a recorded phase result and optional certification
- `./scripts/supernb record-result --initiative-id <id> --status <status> --summary "..." --source manual-override --override-reason "..."` is the controlled manual override path
- `./scripts/supernb migrate-legacy --initiative-id <id>` imports legacy loose `.supernb` files into the initiative workspace and now emits mapping suggestions for the target initiative artifacts
- `./scripts/supernb clean-initiative --initiative-id <id>` previews or archives stale command briefs, dry-run packets, unsupported packets, and older execution artifacts; `--delete` makes hard deletion explicit
- `render-command.sh` validates that the command exists and now renders research-critical fields for product-definition flows
- `make show-command COMMAND=<command>` is the shortcut
- `make render-command COMMAND=<command> GOAL="..." ...` is the structured shortcut
- `make save-command COMMAND=<command> TITLE="..." GOAL="..." ...` is the archival shortcut

Available harness guides:

- [claude-code.md](./claude-code.md)
- [codex.md](./codex.md)
- [opencode.md](./opencode.md)
