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
./scripts/build-impeccable-dist.sh
./scripts/install-opencode.sh /path/to/your-project
```

This script:

- symlinks each `supernb` skill directory directly into `<project>/.opencode/skills/`
- symlinks bundled `sensortower-research`, `flutter-l10n-translation`, and `android-i18n-translation` into `<project>/.opencode/skills/`
- symlinks `impeccable` skills from the isolated local build cache into `<project>/.opencode/skills/`
- repairs previously copied generated `impeccable` skill directories into managed symlinks
- repairs the older aggregate `supernb` symlink layout into per-skill links that OpenCode can discover cleanly

After install, verify the project-local layout with:

```bash
./scripts/supernb verify-installs --harness opencode --project-dir /path/to/your-project
```

This also scans managed `SKILL.md` files for hardcoded harness-specific script/reference paths.

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
make render-command COMMAND=full-product-delivery GOAL="Build a 10M-DAU-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="10m-dau-grade"
make save-command COMMAND=full-product-delivery TITLE="10M DAU Delivery Brief" GOAL="Build a 10M-DAU-grade product" PRODUCT_CATEGORY="finance" MARKETS="SEA" RESEARCH_WINDOW="last 90 days" STACK="your stack" QUALITY_BAR="10m-dau-grade"
```

`make execute-next` currently prepares the execution packet for OpenCode initiatives, but direct CLI invocation is not enabled here yet.
After running the prepared prompt manually, import a structured report first:

```bash
make import-execution INITIATIVE_ID=<id> PHASE=delivery REPORT_JSON=/path/to/report.json
```

Then apply the imported packet:

```bash
make apply-execution INITIATIVE_ID=<id> PACKET=/path/to/packet CERTIFY=1
```

- load `supernb-orchestrator` when the work spans product to delivery
- load `product-research-prd` for research-backed product definition
- load `ui-ux-governance` for design generation or design review
- use upstream `superpowers` for implementation planning and execution

For stable structured invocation, use:

- [commands/README.md](../../commands/README.md)
- [docs/commands/opencode.md](../commands/opencode.md)

Shortcut:

```bash
make show-command COMMAND=ui-ux-upgrade
```

Quickstart: [quickstart.md](../quickstart.md)
