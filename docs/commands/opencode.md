# OpenCode Command Mapping

## Recommended Pattern

Use `supernb` command templates as structured prompts in OpenCode sessions.

Example:

```bash
make show-command COMMAND=ui-ux-upgrade
```

Paste the result into OpenCode and fill the placeholders.

## Relationship To Skills

- OpenCode project skills still come from `.opencode/skills/supernb`
- upstream `superpowers` still provides the base execution plugin
- the command template simply standardizes how the request is framed

## Recommended Uses

- `single-capability-router`
- `ui-ux-upgrade`
- `brainstorm-and-save`
- `full-product-delivery`

