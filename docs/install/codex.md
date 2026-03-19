# Codex Install

Codex is the cleanest environment for the full `supernb` stack because it can use:

- `superpowers` skills directly
- local `supernb` orchestration skills
- local `sensortower-research`
- built `impeccable` Codex bundle

## 1. Sync upstreams and build `impeccable`

```bash
make update
```

## 2. Install into Codex skill discovery

```bash
./scripts/install-codex.sh
```

The script wires these paths into `~/.agents/skills/`:

- `supernb`
- `superpowers`
- `impeccable`
- `sensortower-research`

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
