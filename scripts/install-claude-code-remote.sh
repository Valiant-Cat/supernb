#!/usr/bin/env bash

set -euo pipefail

REPO_DIR="${HOME}/.supernb/supernb"
TARGET_DIR="${HOME}"
SKIP_UPDATE=0
REPO_URL="${SUPERNB_REMOTE_REPO_URL:-https://github.com/WayJerry/supernb.git}"

usage() {
  cat <<'EOF'
One-command remote installer for `supernb` on Claude Code.

Usage:
  install-claude-code-remote.sh [--repo-dir <path>] [--project-dir <path>] [--skip-update]

Options:
  --repo-dir <path>      Where to clone or update supernb. Default: ~/.supernb/supernb
  --project-dir <path>   Optional project-local Claude Code install target. Default: $HOME
  --skip-update          Skip upstream sync/build step after cloning or updating

Examples:
  bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/install-claude-code-remote.sh)
  bash <(curl -fsSL https://raw.githubusercontent.com/WayJerry/supernb/main/scripts/install-claude-code-remote.sh) --project-dir ~/projects/my-app
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir)
      REPO_DIR="${2:-}"
      shift 2
      ;;
    --project-dir)
      TARGET_DIR="${2:-}"
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

mkdir -p "$(dirname "${REPO_DIR}")"

if [[ -d "${REPO_DIR}/.git" ]]; then
  echo "Updating supernb repo at ${REPO_DIR}..."
  bash "${REPO_DIR}/scripts/update-supernb.sh" --skip-upstreams
else
  echo "Cloning supernb into ${REPO_DIR}..."
  git clone "${REPO_URL}" "${REPO_DIR}"
fi

if [[ "${SKIP_UPDATE}" -eq 0 ]]; then
  echo "Syncing upstreams and building provider bundles..."
  bash "${REPO_DIR}/scripts/update-upstreams.sh"
fi

echo "Installing Claude Code assets into ${TARGET_DIR}..."
bash "${REPO_DIR}/scripts/install-claude-code.sh" "${TARGET_DIR}"

echo
echo "supernb Claude Code remote install complete."
echo "Repo dir: ${REPO_DIR}"
echo "Install target: ${TARGET_DIR}"
echo
bash "${REPO_DIR}/scripts/print-next-steps.sh" --harness claude-code --repo-dir "${REPO_DIR}" --project-dir "${TARGET_DIR}"
