# Codex Command Mapping

## Recommended Pattern

Because Codex already discovers `supernb` skills, the simplest stable flow is:

1. print a `supernb` command template
2. paste it into Codex
3. fill in the goal, context, and output fields

Example:

```bash
make show-command COMMAND=implementation-execution
```

Then use the rendered template in Codex.

For a pre-filled prompt:

```bash
make render-command COMMAND=implementation-execution GOAL="Implement the billing module" REPOSITORY="/path/to/repo" STACK="go + react"
```

For initiatives that already have a `next-command.md`, you can execute the current phase directly:

```bash
./scripts/supernb execute-next \
  --initiative-id <initiative-id> \
  --harness codex \
  --project-dir /path/to/repo
```

Then apply the resulting packet:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet \
  --certify
```

For certifiable packets, Codex responses must include the structured `REPORT JSON` block that `execute-next` asks for.
`--dry-run` packets are preview-only and should be rerun before certification.

## Why This Works

- Codex can already discover `supernb` skills through `~/.agents/skills/`
- the command template gives a stable invocation shape
- no extra proprietary command system is required

## Recommended Uses

- `full-product-delivery`
- `single-capability-router`
- `implementation-execution`
- `i18n-localization-governance`
