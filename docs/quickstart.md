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

## 2. Create An Initiative

```bash
./scripts/supernb init-initiative my-product "My Product"
```

Then fill:

- `artifacts/initiatives/<initiative-id>/initiative.yaml`

## 3. Run The Control Plane

```bash
./scripts/supernb run --initiative-id <initiative-id>
```

This writes:

- `artifacts/initiatives/<initiative-id>/run-status.md`
- `artifacts/initiatives/<initiative-id>/run-status.json`
- `artifacts/initiatives/<initiative-id>/next-command.md`
- `artifacts/initiatives/<initiative-id>/phase-packet.md`
- `artifacts/initiatives/<initiative-id>/run-log.md`
- `artifacts/initiatives/<initiative-id>/phase-results/`

## 4. Record The Outcome

After a phase execution, record what happened:

```bash
./scripts/supernb record-result \
  --initiative-id <initiative-id> \
  --status succeeded \
  --summary "Research batch completed"
```

This writes a timestamped result file into `phase-results/`, appends to `run-log.md`, and reruns `supernb run` by default.

## 5. Advance The Gate

When the phase really should advance, write the approval/ready/verified state into the artifacts:

```bash
./scripts/supernb advance-phase \
  --initiative-id <initiative-id> \
  --phase research \
  --status approved \
  --actor supernb
```

This updates the relevant artifact status fields and reruns `supernb run` by default.

## 6. Pick A Command

The three most useful manual entrypoints are:

- `full-product-delivery`
- `single-capability-router`
- `ui-ux-upgrade`

See the raw templates:

```bash
./scripts/supernb show-command full-product-delivery
./scripts/supernb show-command single-capability-router
./scripts/supernb show-command ui-ux-upgrade
```

## 7. Render A Filled Prompt

```bash
./scripts/supernb render-command \
  --command full-product-delivery \
  --goal "Build a commercial-grade product" \
  --repository "https://github.com/example/repo.git" \
  --product-category "finance" \
  --markets "SEA" \
  --research-window "last 90 days" \
  --stack "your stack" \
  --constraints "no MVP shortcuts; commercial quality"
```

## 8. Save The Brief

```bash
./scripts/supernb save-command \
  --command full-product-delivery \
  --title "Commercial Product Delivery Brief" \
  --goal "Build a commercial-grade product" \
  --repository "https://github.com/example/repo.git" \
  --product-category "finance" \
  --markets "SEA" \
  --research-window "last 90 days" \
  --stack "your stack"
```

This stores the prompt in `artifacts/commands/` for reuse and auditability.

## Minimal Daily Workflow

```bash
make bootstrap
make update
make init-initiative INITIATIVE=my-product TITLE="My Product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days"
make run-initiative INITIATIVE_ID=2026-03-19-my-product
make record-result INITIATIVE_ID=2026-03-19-my-product STATUS=succeeded SUMMARY="Research batch completed"
make advance-phase INITIATIVE_ID=2026-03-19-my-product PHASE=research STATUS=approved ACTOR="supernb"
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="commercial-grade"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="commercial-grade"
```

Update shortcuts:

- `make update` updates `supernb` itself when safe, then updates upstreams
- `make update` also writes JSON and Markdown reports to `artifacts/updates/`
- `make update-upstreams` updates only upstream caches

## Harness-Specific Notes

- Codex: restart Codex after install so it reloads skills from `~/.agents/skills/`.
- Claude Code: bootstrap now attempts to install the default upstream `superpowers` plugin automatically if it is missing. See [claude-code.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/claude-code.md).
- OpenCode: bootstrap now ensures upstream `superpowers` is present in project `opencode.json`. See [opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/install/opencode.md).
