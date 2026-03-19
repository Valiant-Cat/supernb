# Claude Code Install

`supernb` on Claude Code uses:

- latest `obra/superpowers` as the default planning and delivery plugin
- local `supernb` skills for orchestration
- bundled `sensortower-research` and translation skills as project-local skills
- built `impeccable` Claude Code bundle for UI/UX work
- optional `superpowers@frad-dotclaude` only when you specifically need the loop workflow

## 1. Bootstrap

Recommended path:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh)
```

If auto-detection does not pick the current project correctly, use the explicit form:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness claude-code --project-dir /path/to/your-project
```

Or from a local clone:

```bash
make bootstrap PROJECT_DIR=/path/to/your-project
```

If auto-detection is ambiguous:

```bash
make bootstrap HARNESS=claude-code PROJECT_DIR=/path/to/your-project
```

This path now:

- installs bundled project-local skills when missing
- skips already present skill paths instead of overwriting them
- auto-installs the default Claude Code `superpowers` plugin when it is not already installed

Manual path:

From this repo:

```bash
make update
```

## 2. Default `superpowers` plugin

`bootstrap` now attempts to install the default upstream plugin automatically.

If your Claude Code setup does not use the official marketplace path, use the upstream marketplace fallback from `obra/superpowers` instead:

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

## 3. Install local `supernb`, bundled skills, and `impeccable` assets into a project

If you want to install into the current project:

```bash
./scripts/install-claude-code.sh /path/to/your-project
```

What the script does:

- symlinks `supernb/skills` to `<project>/.claude/skills/supernb`
- symlinks bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation` into `<project>/.claude/skills/`
- copies the built `impeccable` Claude Code bundle into `<project>/.claude/`
- skips existing paths instead of overwriting them

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

Shortest usage path after install:

```bash
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" STACK="your stack"
```

Use the `supernb` command templates from:

- [commands/README.md](/Users/xiaomiao26_1_26/projects/supernb/commands/README.md)
- [docs/commands/claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/claude-code.md)

Shortcut:

```bash
make show-command COMMAND=full-product-delivery
```

Quickstart: [quickstart.md](/Users/xiaomiao26_1_26/projects/supernb/docs/quickstart.md)

## Notes

- bundled `sensortower-research` is installed as a project-local skill, not a Claude marketplace plugin.
- If you want Claude Code to consume Sensor Tower data directly, expose that workflow separately through your own scripts or MCP setup.
- The default recommendation here follows the current upstream `obra/superpowers` install docs, verified on 2026-03-19 from the project README: https://github.com/obra/superpowers/blob/main/README.md
