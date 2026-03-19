# Claude Code Install

`supernb` on Claude Code uses:

- `superpowers@frad-dotclaude` for planning, BDD execution, and loop automation
- local `supernb` skills for orchestration
- built `impeccable` Claude Code bundle for UI/UX work

## 1. Sync upstreams and build `impeccable`

From this repo:

```bash
make update
```

## 2. Install the FradSer marketplace and plugin

```bash
claude plugin marketplace add FradSer/dotclaude
claude plugin install superpowers@frad-dotclaude
```

Restart Claude Code after install.

## 3. Install local `supernb` and `impeccable` assets into a project

If you want to install into the current project:

```bash
./scripts/install-claude-code.sh /path/to/your-project
```

What the script does:

- symlinks `supernb/skills` to `<project>/.claude/skills/supernb`
- copies the built `impeccable` Claude Code bundle into `<project>/.claude/`

## 4. Recommended Session Flow

1. Start with `product-research-prd`.
2. Write or refine the PRD.
3. Use `ui-ux-governance`.
4. Run `superpowers` planning and execution.
5. Use the Superpower Loop only on explicit bounded tasks.

## Notes

- `sensortower-research` is a local Codex skill, not a Claude marketplace plugin. For Claude Code sessions, use the research outputs generated locally and checked into `artifacts/research/`.
- If you want Claude Code to consume Sensor Tower data directly, expose that workflow separately through your own scripts or MCP setup.

