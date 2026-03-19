# Quickstart

This is the shortest path to get `supernb` installed and used.

Bootstrap behavior:

- installs bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation`
- skips existing skills and plugin installs instead of overwriting them
- auto-installs the default Claude Code `superpowers` plugin when needed
- auto-ensures the OpenCode `superpowers` plugin entry in project `opencode.json`

## 1. Install

Use the bootstrap script:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh)
```

If your machine has multiple supported harnesses installed, pass one explicitly:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness codex
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness claude-code --project-dir /path/to/project
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness opencode --project-dir /path/to/project
```

## 2. Pick A Command

The three most useful entrypoints are:

- `full-product-delivery`
- `single-capability-router`
- `ui-ux-upgrade`

See the raw templates:

```bash
./scripts/show-command-template.sh full-product-delivery
./scripts/show-command-template.sh single-capability-router
./scripts/show-command-template.sh ui-ux-upgrade
```

## 3. Render A Filled Prompt

```bash
./scripts/render-command.sh \
  --command full-product-delivery \
  --goal "Build a commercial-grade product" \
  --repository "https://github.com/example/repo.git" \
  --stack "your stack" \
  --constraints "no MVP shortcuts; commercial quality"
```

## 4. Save The Brief

```bash
./scripts/save-command-brief.sh \
  --command full-product-delivery \
  --title "Commercial Product Delivery Brief" \
  --goal "Build a commercial-grade product" \
  --repository "https://github.com/example/repo.git" \
  --stack "your stack"
```

This stores the prompt in `artifacts/commands/` for reuse and auditability.

## Minimal Daily Workflow

```bash
make bootstrap
make update
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" STACK="your stack"
```

Update shortcuts:

- `make update` updates `supernb` itself when safe, then updates upstreams
- `make update-upstreams` updates only upstream caches

## Harness-Specific Notes

- Codex: restart Codex after install so it reloads skills from `~/.agents/skills/`.
- Claude Code: bootstrap now attempts to install the default upstream `superpowers` plugin automatically if it is missing. See [claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/claude-code.md).
- OpenCode: bootstrap now ensures upstream `superpowers` is present in project `opencode.json`. See [opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/opencode.md).
