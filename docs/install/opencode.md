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
- keeps already-installed managed skills aligned through symlinks
- auto-creates or updates project `opencode.json` so upstream `superpowers` is installed

Manual path:

```bash
make update
```

If you only want upstream caches without touching the current `supernb` checkout:

```bash
make update-upstreams
```

`make update` now also writes JSON and Markdown reports to `artifacts/updates/`.

## 2. Install local project skills and the `impeccable` bundle

```bash
./scripts/install-opencode.sh /path/to/your-project
```

This script:

- symlinks `supernb/skills` into `<project>/.opencode/skills/supernb`
- symlinks bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation` into `<project>/.opencode/skills/`
- symlinks `impeccable` skills from the isolated local build cache into `<project>/.opencode/skills/`
- repairs previously copied generated `impeccable` skill directories into managed symlinks

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
make render-command COMMAND=full-product-delivery GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack"
make save-command COMMAND=full-product-delivery TITLE="Delivery Brief" GOAL="Build a commercial-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack"
```

`make execute-next` currently prepares the execution packet for OpenCode initiatives, but direct CLI invocation is not enabled here yet.
After running the prepared prompt manually, use `make apply-execution INITIATIVE_ID=<id> PACKET=/path/to/packet CERTIFY=1`.

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
