#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_SELF_UPDATE=0
SKIP_UPSTREAMS=0
SKIP_IMPECCABLE_BUILD=0

usage() {
  cat <<'EOF'
Usage: ./scripts/update-supernb.sh [options]

Options:
  --skip-self-update       Do not fetch/pull the current supernb repository
  --skip-upstreams         Do not sync upstream repositories
  --skip-impeccable-build  Pass through to update-upstreams.sh

This command is idempotent:
  - updates supernb itself only when the current repo is clean and on its default branch
  - skips self-update safely when the working tree is dirty or on a non-default branch
  - updates upstream caches and rebuilds impeccable by default
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-self-update)
      SKIP_SELF_UPDATE=1
      shift
      ;;
    --skip-upstreams)
      SKIP_UPSTREAMS=1
      shift
      ;;
    --skip-impeccable-build)
      SKIP_IMPECCABLE_BUILD=1
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

determine_default_branch() {
  local repo_dir="$1"
  local default_branch

  default_branch="$(git -C "${repo_dir}" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  default_branch="${default_branch#origin/}"

  if [[ -n "${default_branch}" ]]; then
    printf '%s\n' "${default_branch}"
    return 0
  fi

  if git -C "${repo_dir}" show-ref --verify --quiet refs/remotes/origin/main; then
    printf 'main\n'
    return 0
  fi

  if git -C "${repo_dir}" show-ref --verify --quiet refs/remotes/origin/master; then
    printf 'master\n'
    return 0
  fi

  return 1
}

update_self_repo() {
  local repo_dir="$1"
  local before_head current_branch default_branch after_head

  if [[ ! -d "${repo_dir}/.git" ]]; then
    echo "supernb self-update skipped: current directory is not a git repository."
    return 0
  fi

  before_head="$(git -C "${repo_dir}" rev-parse --short HEAD)"
  current_branch="$(git -C "${repo_dir}" branch --show-current)"

  git -C "${repo_dir}" fetch --all --prune
  default_branch="$(determine_default_branch "${repo_dir}")" || {
    echo "supernb self-update skipped: could not determine default branch."
    return 0
  }

  if [[ -n "$(git -C "${repo_dir}" status --porcelain)" ]]; then
    echo "supernb self-update skipped: working tree is dirty."
    return 0
  fi

  if [[ "${current_branch}" != "${default_branch}" ]]; then
    echo "supernb self-update skipped: current branch is ${current_branch}, default branch is ${default_branch}."
    return 0
  fi

  git -C "${repo_dir}" pull --ff-only origin "${default_branch}"
  after_head="$(git -C "${repo_dir}" rev-parse --short HEAD)"

  if [[ "${before_head}" == "${after_head}" ]]; then
    echo "supernb self-update: already up to date (${after_head})."
  else
    echo "supernb self-update: ${before_head} -> ${after_head}."
  fi
}

echo "Updating supernb..."

if [[ "${SKIP_SELF_UPDATE}" -eq 0 ]]; then
  update_self_repo "${ROOT_DIR}"
else
  echo "supernb self-update skipped by flag."
fi

if [[ "${SKIP_UPSTREAMS}" -eq 0 ]]; then
  upstream_args=()
  if [[ "${SKIP_IMPECCABLE_BUILD}" -eq 1 ]]; then
    upstream_args+=(--skip-impeccable-build)
  fi
  "${ROOT_DIR}/scripts/update-upstreams.sh" "${upstream_args[@]}"
else
  echo "upstream sync skipped by flag."
fi
