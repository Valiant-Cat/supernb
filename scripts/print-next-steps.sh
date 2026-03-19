#!/usr/bin/env bash

set -euo pipefail

HARNESS=""
REPO_DIR=""
PROJECT_DIR=""

usage() {
  cat <<'EOF'
Usage:
  print-next-steps.sh --harness <codex|claude-code|opencode> [options]

Options:
  --repo-dir <path>      supernb repository path
  --project-dir <path>   Project path for claude-code or opencode
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness)
      HARNESS="${2:-}"
      shift 2
      ;;
    --repo-dir)
      REPO_DIR="${2:-}"
      shift 2
      ;;
    --project-dir)
      PROJECT_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${HARNESS}" ]]; then
  echo "--harness is required." >&2
  exit 1
fi

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_DIR="${PROJECT_DIR:-${PWD}}"

echo "Next steps:"

case "${HARNESS}" in
  codex)
    cat <<EOF
1. Restart Codex so it reloads ~/.agents/skills.
2. Generate a starter prompt:
   ${REPO_DIR}/scripts/show-command-template.sh full-product-delivery
3. Or render a filled command:
   ${REPO_DIR}/scripts/render-command.sh --command full-product-delivery --goal "Build a commercial-grade product" --stack "your stack"

Quickstart:
  ${REPO_DIR}/docs/quickstart.md
EOF
    ;;
  claude-code)
    cat <<EOF
1. Restart Claude Code and open this project:
   ${PROJECT_DIR}
2. Confirm the default superpowers plugin is available in this project.
3. Generate a starter prompt locally:
   ${REPO_DIR}/scripts/show-command-template.sh full-product-delivery

Loop mode is optional and separate:
  ${REPO_DIR}/docs/install/claude-code-loop-mode.md

Quickstart:
  ${REPO_DIR}/docs/quickstart.md
EOF
    ;;
  opencode)
    cat <<EOF
1. Restart OpenCode and open this project:
   ${PROJECT_DIR}
2. Confirm ${PROJECT_DIR}/opencode.json contains upstream superpowers.
3. Generate a starter prompt locally:
   ${REPO_DIR}/scripts/show-command-template.sh full-product-delivery

Quickstart:
  ${REPO_DIR}/docs/quickstart.md
EOF
    ;;
  *)
    echo "Unsupported harness: ${HARNESS}" >&2
    exit 1
    ;;
esac
