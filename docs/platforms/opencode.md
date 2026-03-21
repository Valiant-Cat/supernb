# Supernb for OpenCode

`supernb` on OpenCode uses OpenCode's native project-local plugin/config model while keeping `supernb` skills and supporting assets managed inside the target project.

## What You Get

- upstream `superpowers` plugin entry in `opencode.json`
- local `supernb` project skills
- bundled `sensortower-research` and translation skills as project-local skills
- built `impeccable` OpenCode bundle

## Quick Install

Tell OpenCode:

```text
Open the `.opencode/INSTALL.md` file from the `supernb` repository you are currently browsing and follow that repo's instructions.
```

## Manual Install

```bash
./scripts/build-impeccable-dist.sh
./scripts/install-opencode.sh /path/to/your-project
```

`install-opencode.sh` also ensures your project `opencode.json` includes:

```json
{
  "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"]
}
```

## Verify

```bash
./scripts/supernb verify-installs --harness opencode --project-dir /path/to/your-project
```

## Update

```bash
make update
```

If you only want upstream caches:

```bash
make update-upstreams
```

## How It Works

- OpenCode keeps the upstream `superpowers` plugin in `opencode.json`.
- `supernb` stays project-local: skills, translations, design bundle, and execution control artifacts all live in the repo context.
- `execute-next` is still a prepared-prompt/manual-handoff path for OpenCode rather than a direct CLI bridge.

## Troubleshooting

- Restart OpenCode after updating `opencode.json`.
- If skills are not discovered, inspect `<project>/.opencode/skills/`.
- If delivery work is executed manually in OpenCode, import the structured report with `import-execution` before certification.
