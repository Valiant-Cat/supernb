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
make render-command COMMAND=implementation-execution GOAL="Implement the billing module" STACK="go + react"
```

## Why This Works

- Codex can already discover `supernb` skills through `~/.agents/skills/`
- the command template gives a stable invocation shape
- no extra proprietary command system is required

## Recommended Uses

- `full-product-delivery`
- `single-capability-router`
- `implementation-execution`
- `i18n-localization-governance`
