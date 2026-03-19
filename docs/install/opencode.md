# OpenCode Install

OpenCode should use:

- upstream `superpowers` plugin from git
- local `supernb` project skills
- built `impeccable` OpenCode bundle

## 1. Sync upstreams and build `impeccable`

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
