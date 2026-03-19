# Codex Install

Codex is the cleanest environment for the full `supernb` stack because it can use:

- `superpowers` skills directly
- local `supernb` orchestration skills
- local `sensortower-research`
- built `impeccable` Codex bundle

## 1. Sync upstreams and build `impeccable`

One-command install:

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

Manual path:

```bash
make update
```

## 2. Install into Codex skill discovery

```bash
./scripts/install-codex.sh
```

The script always wires these paths into `~/.agents/skills/`:

- `supernb`
- `superpowers`
- `impeccable`

If local optional skills exist, it also links:

- `sensortower-research`
- `flutter-l10n-translation`
- `android-i18n-translation`

## 3. Restart Codex

Codex discovers skills at startup.

## 4. Recommended Usage

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

## Optional

`superpowers` subagent flows work better with multi-agent enabled in your Codex config.
