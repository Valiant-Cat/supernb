# Supernb for Claude Code

`supernb` on Claude Code gives you the full product-delivery stack plus a managed Ralph Loop runtime for prompt-first planning and delivery.

## What You Get

- latest `obra/superpowers` as the default planning and delivery plugin
- local `supernb` orchestration skills
- bundled `sensortower-research` and translation skills as managed Claude Code skills
- built `impeccable` Claude Code bundle for UI/UX work
- bundled `supernb-loop@supernb` for Ralph Loop enforcement in prompt-first planning and delivery

## Quick Install

Recommended user-global remote install:

```bash
# If you are reading github.com/WayJerry/supernb:
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/install-claude-code-remote.sh) \
  --repo-url https://github.com/WayJerry/supernb.git

# If you are reading github.com/Valiant-Cat/supernb:
bash <(curl -fsSL https://raw.githubusercontent.com/Valiant-Cat/supernb/main/scripts/install-claude-code-remote.sh) \
  --repo-url https://github.com/Valiant-Cat/supernb.git
```

Optional project-local override:

```bash
# WayJerry/supernb:
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/install-claude-code-remote.sh) \
  --repo-url https://github.com/WayJerry/supernb.git \
  --project-dir /path/to/your-project

# Valiant-Cat/supernb:
bash <(curl -fsSL https://raw.githubusercontent.com/Valiant-Cat/supernb/main/scripts/install-claude-code-remote.sh) \
  --repo-url https://github.com/Valiant-Cat/supernb.git \
  --project-dir /path/to/your-project
```

## Manual Install

If you already have the repo locally and want the source-based path:

```bash
./scripts/supernb build-impeccable
./scripts/supernb install-claude-code "$HOME"
```

Optional project-local override:

```bash
./scripts/supernb install-claude-code /path/to/your-project
```

User-global with the raw script:

```bash
./scripts/build-impeccable-dist.sh
./scripts/install-claude-code.sh "$HOME"
```

Optional project-local override:

```bash
./scripts/build-impeccable-dist.sh
./scripts/install-claude-code.sh /path/to/your-project
```

If you need the loop plugin explicitly:

```bash
claude plugin marketplace add /path/to/supernb/bundles/claude-loop-marketplace
claude plugin install supernb-loop@supernb
```

## Verify

User-global:

```bash
./scripts/supernb verify-installs --harness claude-code
```

Project-local:

```bash
./scripts/supernb verify-installs --harness claude-code --project-dir /path/to/your-project
```

Loop smoke verification:

```bash
./scripts/supernb verify-claude-loop --allow-live-run
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

- `install-claude-code-remote.sh` is the primary one-command path. It clones or updates `supernb` into `~/.supernb/supernb`, syncs upstreams, builds the provider bundles, and then runs the Claude Code installer for you.
- `install-claude-code "$HOME"` is the recommended default because it keeps the Claude loop runtime and managed instructions consistent across projects.
- Project-local install remains available when one repository needs its own managed `CLAUDE.md` override or isolated Claude skills.
- `install-claude-code` writes managed `CLAUDE.md` guidance so simple prompts like `use supernb to improve this project` route through the prompt-first control plane.
- For prompt-first planning and delivery, `prompt-bootstrap --start-loop` verifies `supernb-loop@supernb`, starts the Ralph Loop contract, and writes audit evidence alongside the initiative.
- For direct `claude-code` runs, `execute-next` auto-arms Ralph Loop and injects the bundled plugin via `--plugin-dir`.

## Troubleshooting

- If prompt-first planning or delivery says the loop environment is missing, verify `supernb-loop@supernb` is enabled in the active Claude scope.
- If direct bridge works but prompt-first does not, you are likely outside the active Claude Code session or missing `CLAUDE_CODE_SESSION_ID`.
- If the session finishes work but closeout does not pass, run `./scripts/supernb apply-execution --spec <initiative.yaml> --packet <packet-dir> --certify` to inspect blockers.

Detailed loop behavior: [Claude Code Loop Mode](../install/claude-code-loop-mode.md)
