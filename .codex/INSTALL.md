# Installing Supernb for Codex

Follow these steps exactly.

## Quick Path

1. Clone or update the repository:

```bash
# If you are reading github.com/WayJerry/supernb:
if [ -d "$HOME/.codex/supernb/.git" ]; then
  git -C "$HOME/.codex/supernb" pull --ff-only
else
  git clone https://github.com/WayJerry/supernb.git "$HOME/.codex/supernb"
fi

# If you are reading github.com/Valiant-Cat/supernb:
if [ -d "$HOME/.codex/supernb/.git" ]; then
  git -C "$HOME/.codex/supernb" pull --ff-only
else
  git clone https://github.com/Valiant-Cat/supernb.git "$HOME/.codex/supernb"
fi
```

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
