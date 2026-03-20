# Supernb for Codex

`supernb` on Codex uses native skill discovery. This is the cleanest full-stack `supernb` environment when you want planning, delivery, design, research, and subagent-capable execution in one place.

## What You Get

- latest `obra/superpowers` skills through Codex native skill discovery
- local `supernb` orchestration skills
- built `impeccable` Codex bundle
- bundled `sensortower-research` and translation skills

## Quick Install

Tell Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/WayJerry/supernb/refs/heads/main/.codex/INSTALL.md
```

## Manual Install

From a local clone:

```bash
./scripts/build-impeccable-dist.sh
./scripts/install-codex.sh
```

## Verify

```bash
./scripts/supernb verify-installs --harness codex
```

## Update

```bash
make update
```

If you only want upstream caches:

```bash
make update-upstreams
```

## How It Works

- Codex scans `~/.agents/skills/` at startup.
- `install-codex.sh` wires first-level skill entries for `supernb`, upstream `superpowers`, `impeccable`, and bundled skills.
- The install is intentionally native to Codex skill discovery instead of introducing a Codex-specific plugin abstraction.

## Troubleshooting

- Restart Codex after install; skills are discovered at startup.
- If subagent-heavy skills feel limited, enable Codex multi-agent support in your Codex config.
- If skills are missing, inspect `~/.agents/skills/` and rerun `./scripts/supernb verify-installs --harness codex`.
