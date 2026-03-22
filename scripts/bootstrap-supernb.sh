#!/usr/bin/env bash

set -euo pipefail

HARNESS=""
REPO_DIR="${HOME}/.supernb/supernb"
REPO_URL="${SUPERNB_REMOTE_REPO_URL:-}"
PROJECT_DIR=""
SKIP_UPDATE=0

usage() {
  cat <<'EOF'
Compatibility bootstrap for `supernb` platform installs.

Usage:
  bootstrap-supernb.sh [--harness <codex|claude-code|opencode>] [options]

Options:
  --repo-url <url>       Git clone URL for the supernb repository. Recommended for mirrored repos.
  --repo-dir <path>      Where to clone or update supernb. Default: ~/.supernb/supernb
  --project-dir <path>   Project directory for claude-code or opencode installs
  --skip-update          Skip upstream sync/build step

Examples:
  bash <(curl -fsSL https://raw.githubusercontent.com/Valiant-Cat/supernb/main/scripts/bootstrap-supernb.sh) --repo-url https://github.com/Valiant-Cat/supernb.git
  bash <(curl -fsSL https://raw.githubusercontent.com/Valiant-Cat/supernb/main/scripts/bootstrap-supernb.sh) --repo-url https://github.com/Valiant-Cat/supernb.git --harness codex
  bash <(curl -fsSL https://raw.githubusercontent.com/Valiant-Cat/supernb/main/scripts/bootstrap-supernb.sh) --repo-url https://github.com/Valiant-Cat/supernb.git --harness claude-code --project-dir ~/projects/my-app

Prefer the platform-native install docs for day-to-day onboarding:
  Codex:       .codex/INSTALL.md
  Claude Code: docs/platforms/claude-code.md
  OpenCode:    .opencode/INSTALL.md
EOF
}

detect_harness() {
  local probe_dir="${PROJECT_DIR:-${PWD}}"
  local marker=""
  local -a candidates=()

  if [[ -d "${probe_dir}/.claude" ]]; then
    marker="claude-code"
  fi

  if [[ -d "${probe_dir}/.opencode" ]]; then
    if [[ -n "${marker}" && "${marker}" != "opencode" ]]; then
      echo "Could not auto-detect harness: both .claude and .opencode markers exist in ${probe_dir}" >&2
      echo "Pass --harness explicitly." >&2
      return 1
    fi
    marker="opencode"
  fi

  if [[ -n "${marker}" ]]; then
    printf '%s\n' "${marker}"
    return 0
  fi

  command -v codex >/dev/null 2>&1 && candidates+=("codex")
  command -v claude >/dev/null 2>&1 && candidates+=("claude-code")
  command -v opencode >/dev/null 2>&1 && candidates+=("opencode")

  if [[ ${#candidates[@]} -eq 1 ]]; then
    printf '%s\n' "${candidates[0]}"
    return 0
  fi

  if [[ ${#candidates[@]} -eq 0 ]]; then
    echo "Could not auto-detect a supported harness." >&2
    echo "Install one of: codex, claude, opencode; or pass --harness explicitly." >&2
    return 1
  fi

  echo "Could not auto-detect harness because multiple supported CLIs are installed: ${candidates[*]}" >&2
  echo "Pass --harness explicitly." >&2
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="${2:-}"
      shift 2
      ;;
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
  HARNESS="$(detect_harness)"
  echo "Auto-detected compatibility target harness: ${HARNESS}"
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
  bash "${REPO_DIR}/scripts/update-supernb.sh" --skip-upstreams
else
  if [[ -z "${REPO_URL}" ]]; then
    echo "A repository URL is required when ${REPO_DIR} does not exist." >&2
    echo "Pass --repo-url https://github.com/Valiant-Cat/supernb.git or set SUPERNB_REMOTE_REPO_URL." >&2
    exit 1
  fi
  echo "Cloning supernb into ${REPO_DIR}..."
  git clone "${REPO_URL}" "${REPO_DIR}"
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
    "${REPO_DIR}/scripts/install-claude-code.sh" "${PROJECT_DIR:-${HOME}}"
    ;;
  opencode)
    "${REPO_DIR}/scripts/install-opencode.sh" "${PROJECT_DIR:-${PWD}}"
    ;;
esac

echo
echo "supernb compatibility bootstrap complete."
echo "Repo dir: ${REPO_DIR}"
echo "Harness: ${HARNESS}"
echo
next_steps_args=(
  --harness "${HARNESS}"
  --repo-dir "${REPO_DIR}"
)

if [[ "${HARNESS}" == "claude-code" || "${HARNESS}" == "opencode" ]]; then
  next_steps_args+=(--project-dir "${PROJECT_DIR:-${PWD}}")
fi

bash "${REPO_DIR}/scripts/print-next-steps.sh" "${next_steps_args[@]}"
