#!/usr/bin/env bash

set -euo pipefail

HARNESS=""
REPO_DIR="${HOME}/.supernb/supernb"
PROJECT_DIR=""
SKIP_UPDATE=0

usage() {
  cat <<'EOF'
Usage:
  bootstrap-supernb.sh --harness <codex|claude-code|opencode> [options]

Options:
  --repo-dir <path>      Where to clone or update supernb. Default: ~/.supernb/supernb
  --project-dir <path>   Project directory for claude-code or opencode installs
  --skip-update          Skip upstream sync/build step

Examples:
  bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness codex
  bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/bootstrap-supernb.sh) --harness claude-code --project-dir ~/projects/my-app
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
    --skip-update)
      SKIP_UPDATE=1
      shift
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
  usage >&2
  exit 1
fi

case "${HARNESS}" in
  codex|claude-code|opencode) ;;
  *)
    echo "Unsupported harness: ${HARNESS}" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "${REPO_DIR}")"

if [[ -d "${REPO_DIR}/.git" ]]; then
  echo "Updating supernb repo at ${REPO_DIR}..."
  git -C "${REPO_DIR}" fetch --all --prune
  git -C "${REPO_DIR}" checkout main >/dev/null 2>&1 || true
  git -C "${REPO_DIR}" pull --ff-only origin main
else
  echo "Cloning supernb into ${REPO_DIR}..."
  git clone https://github.com/WayJerry/supernb.git "${REPO_DIR}"
fi

if [[ "${SKIP_UPDATE}" -eq 0 ]]; then
  echo "Syncing upstreams and building provider bundles..."
  "${REPO_DIR}/scripts/update-upstreams.sh"
fi

case "${HARNESS}" in
  codex)
    "${REPO_DIR}/scripts/install-codex.sh"
    ;;
  claude-code)
    "${REPO_DIR}/scripts/install-claude-code.sh" "${PROJECT_DIR:-${PWD}}"
    ;;
  opencode)
    "${REPO_DIR}/scripts/install-opencode.sh" "${PROJECT_DIR:-${PWD}}"
    ;;
esac

echo
echo "supernb bootstrap complete."
echo "Repo dir: ${REPO_DIR}"
echo "Harness: ${HARNESS}"

