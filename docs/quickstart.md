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

- `.supernb/initiatives/<initiative-id>/initiative.yaml` in the active product project

## 3. Run The Control Plane

```bash
./scripts/supernb run --initiative-id <initiative-id>
```

This writes:

- `.supernb/initiatives/<initiative-id>/run-status.md`
- `.supernb/initiatives/<initiative-id>/run-status.json`
- `.supernb/initiatives/<initiative-id>/next-command.md`
- `.supernb/initiatives/<initiative-id>/phase-packet.md`
- `.supernb/initiatives/<initiative-id>/run-log.md`
- `.supernb/initiatives/<initiative-id>/phase-results/`
- `.supernb/initiatives/<initiative-id>/executions/`

## 4. Execute The Phase

Run the rendered `next-command.md` through a supported harness CLI:

```bash
./scripts/supernb execute-next \
  --initiative-id <initiative-id> \
  --harness codex \
  --project-dir /path/to/repo
```

Use `--dry-run` first if you only want to prepare the packet and inspect the exact command:

```bash
./scripts/supernb execute-next \
  --initiative-id <initiative-id> \
  --harness codex \
  --project-dir /path/to/repo \
  --dry-run
```

This writes a timestamped execution packet under `executions/` with the prompt copy, `prompt-with-report.md`, request metadata, response, stdout, stderr, and a summary.
It also writes `result-suggestion.md/json` and `phase-readiness.md/json` with completed items, remaining items, evidence artifacts, gate suggestions, and phase-specific structural plus semantic readiness checks.
For planning and delivery work, the packet also records explicit `superpowers` workflow trace and batch commit evidence requirements.
`--dry-run` packets are preview-only and are not certification-grade.
For direct Codex and Claude Code bridging, the captured response must include the structured `REPORT JSON` block; otherwise the packet is downgraded to `needs-follow-up`.

## 5. Apply The Execution Packet

After reviewing the packet, convert it into a phase result:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet
```

If you want it to record the result and then certify the current phase:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet \
  --certify
```

If you want it to record, certify, and advance the phase when certification passes:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet \
  --apply-certification
```

If the phase was executed manually, or via OpenCode after `execute-next` prepared the prompt, import a structured report first:

```bash
./scripts/supernb import-execution \
  --initiative-id <initiative-id> \
  --phase delivery \
  --report-json /path/to/report.json
```

That command creates a normal execution packet under `executions/` so the rest of the workflow can still use `apply-execution`, `certify-phase`, and `advance-phase`.

## 6. Record The Outcome

After a phase execution, record what happened:

```bash
./scripts/supernb record-result \
  --initiative-id <initiative-id> \
  --status succeeded \
  --summary "Research batch completed"
```

This writes a timestamped result file into `phase-results/`, appends to `run-log.md`, and reruns `supernb run` by default.

Use this direct path only when you need to override the packet suggestion manually.

If you are bringing an older loose `.supernb` workspace forward, run:

```bash
./scripts/supernb migrate-legacy \
  --initiative-id <initiative-id> \
  --legacy-root /path/to/.supernb
```

If execution history gets noisy after many previews and retries, inspect cleanup candidates with:

```bash
./scripts/supernb clean-initiative --initiative-id <initiative-id>
```

## 7. Certify The Phase

Before advancing, check whether the current phase artifacts still contain structural gaps or semantic completeness problems:

```bash
./scripts/supernb certify-phase \
  --initiative-id <initiative-id> \
  --phase research
```

If you want it to advance immediately when the phase passes:

```bash
./scripts/supernb certify-phase \
  --initiative-id <initiative-id> \
  --phase research \
  --apply \
  --actor supernb
```

## 8. Advance The Gate

When the phase really should advance, write the approval/ready/verified state into the artifacts:

```bash
./scripts/supernb advance-phase \
  --initiative-id <initiative-id> \
  --phase research \
  --status approved \
  --actor supernb
```

This updates the relevant artifact status fields and reruns `supernb run` by default.

## 9. Pick A Command

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

## 10. Render A Filled Prompt

```bash
./scripts/supernb render-command \
  --command full-product-delivery \
  --goal "Build a 10M-DAU-grade product" \
  --repository "https://github.com/example/repo.git" \
  --product-category "finance" \
  --markets "SEA" \
  --research-window "last 90 days" \
  --stack "your stack" \
  --quality-bar "10m-dau-grade" \
  --constraints "no MVP shortcuts; 10M-DAU-grade quality"
```

## 11. Save The Brief

```bash
./scripts/supernb save-command \
  --command full-product-delivery \
  --title "10M DAU Product Delivery Brief" \
  --goal "Build a 10M-DAU-grade product" \
  --repository "https://github.com/example/repo.git" \
  --product-category "finance" \
  --markets "SEA" \
  --research-window "last 90 days" \
  --stack "your stack" \
  --quality-bar "10m-dau-grade"
```

This stores the prompt in `artifacts/commands/` for reuse and auditability.

## Minimal Daily Workflow

```bash
make bootstrap
make update
make init-initiative INITIATIVE=my-product TITLE="My Product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days"
make run-initiative INITIATIVE_ID=2026-03-19-my-product
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=codex PROJECT_DIR=/path/to/repo DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet APPLY_CERTIFICATION=1
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a 10M-DAU-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="10m-dau-grade"
make save-command COMMAND=full-product-delivery TITLE="10M DAU Delivery Brief" GOAL="Build a 10M-DAU-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="10m-dau-grade"
```

Update shortcuts:

- `make update` updates `supernb` itself when safe, then updates upstreams
- `make update` also writes JSON and Markdown reports to `artifacts/updates/`
- `make update-upstreams` updates only upstream caches
- `make verify-installs` checks whether key harness skills are discoverable at the expected first-level locations and whether managed `SKILL.md` files still contain hardcoded harness-specific script/reference paths

## Harness-Specific Notes

- Codex: restart Codex after install so it reloads skills from `~/.agents/skills/`.
- Claude Code: bootstrap now attempts to install the default upstream `superpowers` plugin automatically if it is missing. See [claude-code.md](./install/claude-code.md).
- OpenCode: bootstrap now ensures upstream `superpowers` is present in project `opencode.json`. See [opencode.md](./install/opencode.md).
