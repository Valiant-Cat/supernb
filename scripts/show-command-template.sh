#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMAND_NAME="${1:-}"

if [[ -z "${COMMAND_NAME}" ]]; then
  echo "Usage: ./scripts/show-command-template.sh <command-name>" >&2
  exit 1
fi

COMMAND_FILE="${ROOT_DIR}/commands/${COMMAND_NAME}.md"

if [[ ! -f "${COMMAND_FILE}" ]]; then
  echo "Unknown command: ${COMMAND_NAME}" >&2
  echo "" >&2
  echo "Available commands:" >&2
  find "${ROOT_DIR}/commands" -maxdepth 1 -type f -name '*.md' ! -name 'README.md' -exec basename {} .md \; | sort >&2
  exit 1
fi

cat "${COMMAND_FILE}"
