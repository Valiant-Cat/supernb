# Codex Install

Codex is the cleanest environment for the full `supernb` stack because it can use:

- `superpowers` skills directly
- local `supernb` orchestration skills
- bundled `sensortower-research`
- built `impeccable` Codex bundle
- bundled translation skills

## 1. Bootstrap

Recommended path:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh)
```

Or explicitly:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness codex
```

Or from a local clone:

```bash
make bootstrap
```

If auto-detection is ambiguous:

```bash
make bootstrap HARNESS=codex
```

This path installs all bundled `supernb` skills in one pass and skips any skill links that are already present.

Manual path if you want to run sync/build separately:

```bash
make update
```

If you only want upstream caches without touching the current `supernb` checkout:

```bash
make update-upstreams
```

`make update` now also writes JSON and Markdown reports to `artifacts/updates/`.

## 2. Install into Codex skill discovery

```bash
./scripts/install-codex.sh
```

The script wires these paths into `~/.agents/skills/` when missing:

- each `supernb` skill as a first-level Codex skill entry
- each upstream `superpowers` skill as a first-level Codex skill entry
- each `impeccable` skill as a first-level Codex skill entry
- `sensortower-research`
- `flutter-l10n-translation`
- `android-i18n-translation`

`impeccable` now points at the isolated local build cache under `.supernb-cache/impeccable-dist` rather than depending on mutable files inside the upstream clone.
The installer also repairs the older aggregate-link layout so Codex sees individual skills instead of a hidden nested bundle.

## 3. Restart Codex

Codex discovers skills at startup.

## 4. Recommended Usage

Shortest usage path after install:

```bash
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack"
make execute-next INITIATIVE_ID=2026-03-19-my-product HARNESS=codex PROJECT_DIR=/path/to/repo DRY_RUN=1
make apply-execution INITIATIVE_ID=2026-03-19-my-product PACKET=/path/to/packet CERTIFY=1
```

Ask for one of these flows:

- use `supernb-orchestrator` to run end-to-end product delivery
- use `product-research-prd` to generate a research-backed PRD
- use `ui-ux-governance` before or after frontend work
- use `autonomous-delivery` once PRD and design are approved

For stable structured invocation, use:

- [commands/README.md](/Users/xiaomiao26_1_26/projects/supernb/commands/README.md)
- [docs/commands/codex.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/codex.md)

Shortcut:

```bash
make show-command COMMAND=single-capability-router
```

Quickstart: [quickstart.md](/Users/xiaomiao26_1_26/projects/supernb/docs/quickstart.md)

## Optional

`superpowers` subagent flows work better with multi-agent enabled in your Codex config.
