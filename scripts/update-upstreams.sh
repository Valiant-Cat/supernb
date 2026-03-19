#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstreams"
BUILD_IMPECCABLE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-impeccable-build)
      BUILD_IMPECCABLE=0
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/update-upstreams.sh [--skip-impeccable-build]

Clones or fast-forwards:
  - obra/superpowers
  - FradSer/dotclaude
  - pbakaus/impeccable

By default it also builds impeccable dist bundles.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "${UPSTREAM_DIR}"

update_repo() {
  local name="$1"
  local url="$2"
  local target="${UPSTREAM_DIR}/${name}"

  if [[ -d "${target}/.git" ]]; then
    echo "Updating ${name}..."
    git -C "${target}" fetch --all --prune

    local default_branch
    default_branch="$(git -C "${target}" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
    default_branch="${default_branch#origin/}"

    if [[ -z "${default_branch}" ]]; then
      if git -C "${target}" show-ref --verify --quiet refs/remotes/origin/main; then
        default_branch="main"
      elif git -C "${target}" show-ref --verify --quiet refs/remotes/origin/master; then
        default_branch="master"
      else
        echo "Could not determine default branch for ${name}" >&2
        exit 1
      fi
    fi

    git -C "${target}" checkout "${default_branch}" >/dev/null 2>&1 || true
    git -C "${target}" pull --ff-only origin "${default_branch}"
  else
    echo "Cloning ${name}..."
    git clone "${url}" "${target}"
  fi
}

update_repo "superpowers" "https://github.com/obra/superpowers.git"
update_repo "dotclaude" "https://github.com/FradSer/dotclaude.git"
update_repo "impeccable" "https://github.com/pbakaus/impeccable.git"

if [[ "${BUILD_IMPECCABLE}" -eq 1 ]]; then
  "${ROOT_DIR}/scripts/build-impeccable-dist.sh"
fi

