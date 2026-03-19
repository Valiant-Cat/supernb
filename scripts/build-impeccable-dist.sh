#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMPECCABLE_DIR="${ROOT_DIR}/upstreams/impeccable"

if [[ ! -d "${IMPECCABLE_DIR}/.git" ]]; then
  echo "impeccable clone not found at ${IMPECCABLE_DIR}" >&2
  echo "Run ./scripts/update-upstreams.sh first." >&2
  exit 1
fi

if ! command -v bun >/dev/null 2>&1; then
  echo "bun is required to build impeccable bundles." >&2
  exit 1
fi

echo "Installing impeccable dependencies..."
bun install --frozen-lockfile --cwd "${IMPECCABLE_DIR}"

echo "Building impeccable provider bundles..."
bun run --cwd "${IMPECCABLE_DIR}" build

echo "Built impeccable dist at ${IMPECCABLE_DIR}/dist"

