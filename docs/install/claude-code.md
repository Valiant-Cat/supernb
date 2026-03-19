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

Direct project-local install path:

```bash
./scripts/supernb install-claude-code /path/to/your-project
```

If you are already inside the target project:

```bash
/path/to/supernb/scripts/supernb install-claude-code
```

Direct user-global install into `~/.claude`:

```bash
./scripts/supernb install-claude-code "$HOME"
```

This path now:

- installs bundled project-local skills when missing
- keeps already-installed managed skills aligned through symlinks
- auto-installs the default Claude Code `superpowers` plugin when it is not already installed
- auto-enables the plugin when it is already installed but currently disabled

Manual path:

From this repo:

```bash
make update
```

If you only want upstream caches without touching the current `supernb` checkout:

```bash
make update-upstreams
```

`make update` now also writes JSON and Markdown reports to `artifacts/updates/`.

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
./scripts/supernb install-claude-code /path/to/your-project
make install-claude-code PROJECT_DIR=/path/to/your-project
```

If you want a user-global install instead of a per-project install:

```bash
./scripts/install-claude-code.sh "$HOME"
./scripts/supernb install-claude-code "$HOME"
```

After install, verify the user-global layout with:

```bash
./scripts/supernb verify-installs --harness claude-code
```

If you also want to verify a project-local Claude Code install:

```bash
./scripts/supernb verify-installs --harness claude-code --project-dir /path/to/your-project
```

This also scans managed `SKILL.md` files for hardcoded harness-specific script/reference paths.

What the script does:

- symlinks each `supernb` skill directory directly into `<project>/.claude/skills/`
- symlinks bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation` into `<project>/.claude/skills/`
- symlinks `impeccable` skills from the isolated local build cache into `<project>/.claude/skills/`
- repairs previously copied generated `impeccable` skill directories into managed symlinks
- repairs the older aggregate `supernb` symlink layout into per-skill links that Claude Code can actually list

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
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack"
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=claude-code PROJECT_DIR=/path/to/project DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet CERTIFY=1
```

Use the `supernb` command templates from:

- [commands/README.md](../../commands/README.md)
- [docs/commands/claude-code.md](../commands/claude-code.md)

Shortcut:

```bash
make show-command COMMAND=full-product-delivery
```

Quickstart: [quickstart.md](../quickstart.md)

## Notes

- bundled `sensortower-research` is installed as a project-local skill, not a Claude marketplace plugin.
- If you want Claude Code to consume Sensor Tower data directly, expose that workflow separately through your own scripts or MCP setup.
- The default recommendation here follows the current upstream `obra/superpowers` install docs, verified on 2026-03-19 from the project README: https://github.com/obra/superpowers/blob/main/README.md
