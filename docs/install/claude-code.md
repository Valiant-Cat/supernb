# Claude Code Install

`supernb` on Claude Code uses:

- latest `obra/superpowers` as the default planning and delivery plugin
- local `supernb` skills for orchestration
- bundled `sensortower-research` and translation skills as managed Claude Code skills in the selected install scope
- built `impeccable` Claude Code bundle for UI/UX work
- `superpowers@frad-dotclaude` when you need Ralph Loop enforcement for Claude Code prompt-first planning or delivery

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
./scripts/supernb build-impeccable
./scripts/supernb install-claude-code /path/to/your-project
```

If you are already inside the target project:

```bash
/path/to/supernb/scripts/supernb install-claude-code
```

Direct user-global install into `~/.claude`:

```bash
./scripts/supernb build-impeccable
./scripts/supernb install-claude-code "$HOME"
```

This path now:

- installs bundled managed skills into the selected Claude Code scope
- keeps already-installed managed skills aligned through symlinks
- auto-installs the default Claude Code `superpowers` plugin when it is not already installed
- auto-enables the plugin when it is already installed but currently disabled
- if you target `"$HOME"`, the skills live in `~/.claude/skills/` and target projects do not need their own `.claude/` directory

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
./scripts/build-impeccable-dist.sh
./scripts/install-claude-code.sh /path/to/your-project
./scripts/supernb install-claude-code /path/to/your-project
make install-claude-code PROJECT_DIR=/path/to/your-project
```

If you want a user-global install instead of a per-project install:

```bash
./scripts/build-impeccable-dist.sh
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

## 4. Ralph Loop Mode For Prompt-First Planning And Delivery

Use this mode when Claude Code is going to run prompt-first `supernb` planning or delivery and you need the session to keep iterating until the completion promise is actually true.

```bash
claude plugin marketplace add FradSer/dotclaude
claude plugin install superpowers@frad-dotclaude
```

Rules:

- do not keep both same-named `superpowers` plugins installed side by side in one Claude Code environment
- keep the latest `obra/superpowers` as the default baseline in environments that do not need Ralph Loop
- use the Frad plugin in the Claude Code environment that will run the bounded prompt-first planning or delivery batch
- do not use this mode for vague unbounded prompts

## 5. Recommended Session Flow

1. Start with `product-research-prd`.
2. Write or refine the PRD.
3. Use `ui-ux-governance`.
4. Run the latest `superpowers` planning and execution flow.
5. If the active Claude Code session will execute planning or delivery by prompt-first `supernb`, switch to the Ralph Loop-enabled environment before starting the batch.

## 5A. Prompt-First Flow

If you mainly use Claude Code by saying things like "use supernb" or "使用 supernb 完善这个项目", that is valid, but the skill should still drive the control plane under the hood.

Expected behavior:

1. The `supernb` skill resolves the current initiative.
2. It runs:

```bash
./scripts/supernb prompt-sync --initiative-id <initiative-id> --start-loop
```

3. It reads `.supernb/initiatives/<initiative-id>/prompt-session.md`.
4. For planning and delivery on Claude Code, that same command first verifies that the active Claude environment has `superpowers@frad-dotclaude` enabled, then starts the generated Ralph Loop contract in the current Claude session and writes loop audit files alongside the initiative.
5. It performs the requested phase work.
6. Before stopping, it fills `.supernb/initiatives/<initiative-id>/prompt-report-template.json`, then runs `import-execution` and `apply-execution`.

Without that closeout, Claude Code may have changed code while leaving `run-status`, execution packets, certification, and debug logs stale.
Without Ralph Loop in planning or delivery, Claude Code can still self-terminate early, so those runs should not be treated as clean certification evidence.

## 6. Command Templates

Shortest usage path after install:

```bash
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a 10M-DAU-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="10m-dau-grade"
make save-command COMMAND=full-product-delivery TITLE="10M DAU Delivery Brief" GOAL="Build a 10M-DAU-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="10m-dau-grade"
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=claude-code PROJECT_DIR=/path/to/project DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet CERTIFY=1
```

When you switch from `DRY_RUN=1` to a real bridged run, keep the `REPORT JSON` block in Claude Code's final response.
Without that block, the packet is marked `needs-follow-up` and certification will not treat it as clean execution evidence.
For direct `claude-code` planning or delivery runs, `execute-next` also auto-arms Ralph Loop, injects the bundled `dotclaude` plugin via a session-local `--plugin-dir`, binds a generated Claude session id, waits until the audit watcher has observed the loop state file, and then writes packet-local audit files. Prompt-first sessions still need the active Claude environment to have `superpowers@frad-dotclaude` enabled because the running session cannot retrofit its own hooks.

If you want a real local smoke check for the direct CLI path, run:

```bash
./scripts/supernb verify-claude-loop --allow-live-run
```

That command intentionally invokes a live `claude -p` session and only passes if the audit evidence proves a genuine second Ralph Loop iteration and clean state removal.

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
