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

## 2. Install into Codex skill discovery

```bash
./scripts/install-codex.sh
```

The script wires these paths into `~/.agents/skills/` when missing:

- `supernb`
- `superpowers`
- `impeccable`

- `sensortower-research`
- `flutter-l10n-translation`
- `android-i18n-translation`

## 3. Restart Codex

Codex discovers skills at startup.

## 4. Recommended Usage

Shortest usage path after install:

```bash
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" STACK="your stack"
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
