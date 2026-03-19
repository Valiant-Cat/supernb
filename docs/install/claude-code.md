# Claude Code Install

`supernb` on Claude Code uses:

- latest `obra/superpowers` as the default planning and delivery plugin
- local `supernb` skills for orchestration
- built `impeccable` Claude Code bundle for UI/UX work
- optional `superpowers@frad-dotclaude` only when you specifically need the loop workflow

## 1. Sync upstreams and build `impeccable`

One-command install:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness claude-code --project-dir /path/to/your-project
```

Or from a local clone:

```bash
make bootstrap HARNESS=claude-code PROJECT_DIR=/path/to/your-project
```

Manual path:

From this repo:

```bash
make update
```

## 2. Install the default `superpowers` plugin

```bash
/plugin install superpowers@claude-plugins-official
```

Restart Claude Code after install.

If your Claude Code setup does not use the official marketplace path, use the upstream marketplace fallback from `obra/superpowers` instead:

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

## 3. Install local `supernb` and `impeccable` assets into a project

If you want to install into the current project:

```bash
./scripts/install-claude-code.sh /path/to/your-project
```

What the script does:

- symlinks `supernb/skills` to `<project>/.claude/skills/supernb`
- copies the built `impeccable` Claude Code bundle into `<project>/.claude/`

## 4. Optional Frad Loop Mode

Only use this mode if you need the loop executor and are willing to replace the default Claude Code `superpowers` plugin for that environment.

```bash
claude plugin marketplace add FradSer/dotclaude
claude plugin install superpowers@frad-dotclaude
```

Rules:

- do not keep both same-named `superpowers` plugins installed side by side in one Claude Code environment
- prefer the latest `obra/superpowers` as the default baseline
- use the Frad plugin only for bounded loop-oriented execution sessions

## 5. Recommended Session Flow

1. Start with `product-research-prd`.
2. Write or refine the PRD.
3. Use `ui-ux-governance`.
4. Run the latest `superpowers` planning and execution flow.
5. Switch to the Frad plugin only if you explicitly need Superpower Loop behavior for a bounded task.

## 6. Command Templates

Use the `supernb` command templates from:

- [commands/README.md](/Users/xiaomiao26_1_26/projects/supernb/commands/README.md)
- [docs/commands/claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/claude-code.md)

Shortcut:

```bash
make show-command COMMAND=full-product-delivery
```

## Notes

- `sensortower-research` is a local Codex skill, not a Claude marketplace plugin. For Claude Code sessions, use the research outputs generated locally and checked into `artifacts/research/`.
- If you want Claude Code to consume Sensor Tower data directly, expose that workflow separately through your own scripts or MCP setup.
- The default recommendation here follows the current upstream `obra/superpowers` install docs, verified on 2026-03-19 from the project README: https://github.com/obra/superpowers/blob/main/README.md
