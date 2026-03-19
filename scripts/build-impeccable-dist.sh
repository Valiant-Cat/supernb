#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMPECCABLE_DIR="${ROOT_DIR}/upstreams/impeccable"
IMPECCABLE_CACHE_DIR="${ROOT_DIR}/.supernb-cache/impeccable-dist"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/supernb-impeccable-build-XXXXXX")"
WORK_SOURCE_DIR="${WORK_DIR}/impeccable"

cleanup() {
  rm -rf "${WORK_DIR}"
}

trap cleanup EXIT

if [[ ! -d "${IMPECCABLE_DIR}/.git" ]]; then
  echo "impeccable clone not found at ${IMPECCABLE_DIR}" >&2
  echo "Run ./scripts/update-upstreams.sh first." >&2
  exit 1
fi

if ! command -v bun >/dev/null 2>&1; then
  echo "bun is required to build impeccable bundles." >&2
  exit 1
fi

mkdir -p "$(dirname "${IMPECCABLE_CACHE_DIR}")"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude .git "${IMPECCABLE_DIR}/" "${WORK_SOURCE_DIR}/"
else
  cp -R "${IMPECCABLE_DIR}" "${WORK_SOURCE_DIR}"
  rm -rf "${WORK_SOURCE_DIR}/.git"
fi

echo "Installing impeccable dependencies in isolated build workspace..."
bun install --frozen-lockfile --cwd "${WORK_SOURCE_DIR}"

echo "Building impeccable provider bundles..."
bun run --cwd "${WORK_SOURCE_DIR}" build

rm -rf "${IMPECCABLE_CACHE_DIR}"
mkdir -p "${IMPECCABLE_CACHE_DIR}"
cp -R "${WORK_SOURCE_DIR}/dist/." "${IMPECCABLE_CACHE_DIR}/"

echo "Built impeccable dist at ${IMPECCABLE_CACHE_DIR}"
