# Installing Supernb for Codex

Follow these steps exactly.

## Quick Path

1. Clone or update the repository:

```bash
if [ -d "$HOME/.codex/supernb/.git" ]; then
  git -C "$HOME/.codex/supernb" pull --ff-only
else
  git clone https://github.com/<repo-owner>/supernb.git "$HOME/.codex/supernb"
fi
```

Replace `<repo-owner>` with the owner of the `supernb` repository you are currently using.

2. Build bundled provider assets:

```bash
cd "$HOME/.codex/supernb"
./scripts/update-upstreams.sh
```

3. Install Codex-visible skills:

```bash
./scripts/install-codex.sh
```

4. Restart Codex.

5. Verify:

```bash
./scripts/supernb verify-installs --harness codex
```

## What This Installs

- `supernb` orchestration skills
- upstream `superpowers` skills
- built `impeccable` Codex bundle
- bundled `sensortower-research`
- bundled translation skills
