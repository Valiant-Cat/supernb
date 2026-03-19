# OpenCode Install

OpenCode should use:

- upstream `superpowers` plugin from git
- local `supernb` project skills
- bundled `sensortower-research` and translation skills as project-local skills
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

This path now:

- installs bundled project-local skills when missing
- skips already present skill paths instead of overwriting them
- auto-creates or updates project `opencode.json` so upstream `superpowers` is installed

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
- symlinks bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation` into `<project>/.opencode/skills/`
- copies the built `impeccable` OpenCode bundle into `<project>/.opencode/`
- skips existing paths instead of overwriting them

## 3. Ensure upstream `superpowers` in `opencode.json`

`bootstrap` now ensures this entry exists in project `opencode.json`:

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
