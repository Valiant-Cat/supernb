# Installing Supernb for OpenCode

Follow these steps exactly.

## Quick Path

1. Clone or update the repository:

```bash
if [ -d "$HOME/.supernb/supernb/.git" ]; then
  git -C "$HOME/.supernb/supernb" pull --ff-only
else
  git clone https://github.com/<repo-owner>/supernb.git "$HOME/.supernb/supernb"
fi
```

Replace `<repo-owner>` with the owner of the `supernb` repository you are currently using.

2. Build bundled provider assets:

```bash
cd "$HOME/.supernb/supernb"
./scripts/update-upstreams.sh
```

3. Install OpenCode assets into the current project:

```bash
./scripts/install-opencode.sh "$PWD"
```

4. Restart OpenCode.

5. Verify:

```bash
./scripts/supernb verify-installs --harness opencode --project-dir "$PWD"
```

## What This Installs

- project-local `supernb` skills
- project-local bundled `sensortower-research`
- project-local translation skills
- built `impeccable` OpenCode bundle
- upstream `superpowers` plugin entry in `opencode.json`
