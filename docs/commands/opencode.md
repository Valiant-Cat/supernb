# OpenCode Command Mapping

## Recommended Pattern

Use `supernb` command templates as structured prompts in OpenCode sessions.

Example:

```bash
make show-command COMMAND=ui-ux-upgrade
```

Paste the result into OpenCode and fill the placeholders.

For a pre-filled prompt:

```bash
make render-command COMMAND=ui-ux-upgrade GOAL="Upgrade the checkout UX" REPOSITORY="/path/to/repo" STACK="react"
```

`supernb execute-next` will still prepare an execution packet for OpenCode initiatives, but direct CLI bridging is not enabled yet because the local OpenCode CLI contract is not standardized in this repo.
You can still use `./scripts/supernb apply-execution --initiative-id <id> --packet <dir>` after the prompt is run manually.

## Relationship To Skills

- OpenCode project skills are now installed as first-level entries under `.opencode/skills/`
- upstream `superpowers` still provides the base execution plugin
- the command template simply standardizes how the request is framed

## Recommended Uses

- `single-capability-router`
- `ui-ux-upgrade`
- `brainstorm-and-save`
- `full-product-delivery`
