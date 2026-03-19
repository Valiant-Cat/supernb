# OpenCode Install

OpenCode should use:

- upstream `superpowers` plugin from git
- local `supernb` project skills
- built `impeccable` OpenCode bundle

## 1. Bootstrap

Recommended path:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh)
```

If auto-detection does not pick the current project correctly, use the explicit form:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness opencode --project-dir /path/to/your-project
```

Or from a local clone:

```bash
make bootstrap PROJECT_DIR=/path/to/your-project
```

If auto-detection is ambiguous:

```bash
make bootstrap HARNESS=opencode PROJECT_DIR=/path/to/your-project
```

Manual path:

```bash
make update
```

## 2. Install local project skills and the `impeccable` bundle

```bash
./scripts/install-opencode.sh /path/to/your-project
```

This script:

- symlinks `supernb/skills` into `<project>/.opencode/skills/supernb`
- copies the built `impeccable` OpenCode bundle into `<project>/.opencode/`

## 3. Add upstream `superpowers` to `opencode.json`

Add this to your global or project `opencode.json`:

```json
{
  "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"]
}
```

Restart OpenCode.

## 4. Usage

Shortest usage path after install:

```bash
make show-command COMMAND=full-product-delivery
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" STACK="your stack"
```

- load `supernb/supernb-orchestrator` when the work spans product to delivery
- load `supernb/product-research-prd` for research-backed product definition
- load `supernb/ui-ux-governance` for design generation or design review
- use upstream `superpowers` for implementation planning and execution

For stable structured invocation, use:

- [commands/README.md](/Users/xiaomiao26_1_26/projects/supernb/commands/README.md)
- [docs/commands/opencode.md](/Users/xiaomiao26_1_26/projects/supernb/docs/commands/opencode.md)

Shortcut:

```bash
make show-command COMMAND=ui-ux-upgrade
```

Quickstart: [quickstart.md](/Users/xiaomiao26_1_26/projects/supernb/docs/quickstart.md)
