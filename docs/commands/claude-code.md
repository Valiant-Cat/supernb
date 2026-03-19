# Claude Code Command Mapping

## Recommended Pattern

Use a `supernb` command template as the first structured instruction in a session.

Example:

```text
Use supernb command: full-product-delivery
Goal: Build a commercial-grade product.
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
./scripts/supernb render-command --command full-product-delivery --goal "Build a commercial-grade product" --product-category "finance" --markets "SEA" --research-window "last 90 days" --stack "nextjs"
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

## Notes

- `supernb` skills are project-local guidance.
- upstream `superpowers` remains the main workflow engine
- the Frad plugin remains optional for bounded loop sessions
- this mapping intentionally avoids inventing a fake native Claude Code command system for `supernb`
