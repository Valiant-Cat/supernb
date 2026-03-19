# Claude Code Command Mapping

## Recommended Pattern

Use a `supernb` command template as the first structured instruction in a session.

Example:

```text
Use supernb command: full-product-delivery
Goal: Build a commercial-grade product.
Context: <repo, stack, market, constraints>
Output: <artifacts and implementation expectations>
```

## How To Get The Template

From this repo:

```bash
make show-command COMMAND=full-product-delivery
```

Or:

```bash
./scripts/show-command-template.sh full-product-delivery
```

Then paste the template into Claude Code and fill the placeholders.

For a pre-filled prompt:

```bash
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" STACK="nextjs"
```

## Notes

- `supernb` skills are project-local guidance.
- upstream `superpowers` remains the main workflow engine
- the Frad plugin remains optional for bounded loop sessions
- this mapping intentionally avoids inventing a fake native Claude Code command system for `supernb`
