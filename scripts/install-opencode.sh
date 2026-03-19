#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-${ROOT_DIR}}"
OPENCODE_DIR="${TARGET_DIR}/.opencode"
IMPECCABLE_OPENCODE_DIR="${ROOT_DIR}/upstreams/impeccable/dist/opencode/.opencode"

if [[ ! -d "${IMPECCABLE_OPENCODE_DIR}" ]]; then
  echo "Built impeccable OpenCode bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

mkdir -p "${OPENCODE_DIR}/skills"
cp -R "${IMPECCABLE_OPENCODE_DIR}/." "${OPENCODE_DIR}/"
ln -sfn "${ROOT_DIR}/skills" "${OPENCODE_DIR}/skills/supernb"

cat <<EOF
Installed project-local assets into ${TARGET_DIR}

Add this plugin entry to your opencode.json:
{
  "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"]
}

Restart OpenCode after saving the config.
EOF

