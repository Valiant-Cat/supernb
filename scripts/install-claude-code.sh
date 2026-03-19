#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${1:-${ROOT_DIR}}"
CLAUDE_DIR="${TARGET_DIR}/.claude"
IMPECCABLE_CLAUDE_DIR="${ROOT_DIR}/upstreams/impeccable/dist/claude-code/.claude"

if [[ ! -d "${IMPECCABLE_CLAUDE_DIR}" ]]; then
  echo "Built impeccable Claude Code bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

mkdir -p "${CLAUDE_DIR}/skills"
cp -R "${IMPECCABLE_CLAUDE_DIR}/." "${CLAUDE_DIR}/"
ln -sfn "${ROOT_DIR}/skills" "${CLAUDE_DIR}/skills/supernb"

cat <<EOF
Installed project-local assets into ${TARGET_DIR}

Next, install the FradSer plugin in Claude Code:
  claude plugin marketplace add FradSer/dotclaude
  claude plugin install superpowers@frad-dotclaude

Restart Claude Code after plugin install.
EOF

