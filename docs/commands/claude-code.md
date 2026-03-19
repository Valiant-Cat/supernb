# Claude Code Command Mapping

## Recommended Pattern

Use a `supernb` command template as the first structured instruction in a session.

Example:

```text
Use supernb command: full-product-delivery
Goal: Build a 10M-DAU-grade product.
Context:
- repository: <repo>
- stack: <stack>
- product category: <category>
- markets: <market or countries>
- research window: <date window>
- constraints: <constraints>
Output: <artifacts and implementation expectations>
```

## How To Get The Template

From this repo:

```bash
./scripts/supernb show-command full-product-delivery
```

Or:

```bash
make show-command COMMAND=full-product-delivery
```

Then paste the template into Claude Code and fill the placeholders.

For a pre-filled prompt:

```bash
./scripts/supernb render-command --command full-product-delivery --goal "Build a 10M-DAU-grade product" --product-category "finance" --markets "SEA" --research-window "last 90 days" --stack "nextjs" --quality-bar "10m-dau-grade"
```

For initiatives that already have a `next-command.md`, you can bridge the current phase directly into Claude Code:

```bash
./scripts/supernb execute-next \
  --initiative-id <initiative-id> \
  --harness claude-code \
  --project-dir /path/to/project
```

Then apply the resulting packet:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet \
  --certify
```

For certifiable packets, Claude Code responses must include the structured `REPORT JSON` block that `execute-next` asks for.
`--dry-run` packets are preview-only and should be rerun before certification.

## Notes

- `supernb` skills may be installed project-locally or user-globally, depending on how you ran the installer.
- upstream `superpowers` remains the main workflow engine
- for prompt-first planning and delivery, Claude Code should run in a Ralph Loop-enabled environment instead of relying on self-judged completion
- this mapping intentionally avoids inventing a fake native Claude Code command system for `supernb`
