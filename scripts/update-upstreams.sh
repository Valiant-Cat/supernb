#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstreams"
BUILD_IMPECCABLE=1
REPORT_FILE=""
REPORT_LINES_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-impeccable-build)
      BUILD_IMPECCABLE=0
      shift
      ;;
    --report-file)
      REPORT_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/update-upstreams.sh [--skip-impeccable-build] [--report-file <path>]

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

if [[ -n "${REPORT_FILE}" ]]; then
  mkdir -p "$(dirname "${REPORT_FILE}")"
  REPORT_LINES_FILE="$(mktemp)"
fi

record_repo_status() {
  local name="$1"
  local status="$2"
  local before_commit="$3"
  local after_commit="$4"
  local default_branch="$5"
  local message="$6"

  if [[ -n "${REPORT_LINES_FILE}" ]]; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${name}" \
      "${status}" \
      "${before_commit}" \
      "${after_commit}" \
      "${default_branch}" \
      "${message}" >>"${REPORT_LINES_FILE}"
  fi
}

repair_impeccable_generated_dirty_state() {
  local target="$1"
  local backup_dir="${ROOT_DIR}/.supernb-cache/upstream-repair"
  local backup_file
  local dirty_files=()
  local line path

  while IFS= read -r line; do
    path="${line:3}"
    [[ -n "${path}" ]] && dirty_files+=("${path}")
  done < <(git -C "${target}" status --porcelain)

  if [[ ${#dirty_files[@]} -eq 0 ]]; then
    return 0
  fi

  local dirty_file
  for dirty_file in "${dirty_files[@]}"; do
    case "${dirty_file}" in
      .claude/skills/*/SKILL.md|public/css/styles.css) ;;
      *)
        return 1
        ;;
    esac
  done

  mkdir -p "${backup_dir}"
  backup_file="${backup_dir}/impeccable-generated-dirty-$(date +%Y%m%d-%H%M%S).patch"
  git -C "${target}" diff -- "${dirty_files[@]}" > "${backup_file}"
  git -C "${target}" restore --worktree --staged -- "${dirty_files[@]}"

  echo "impeccable: repaired old generated dirty state."
  echo "impeccable: backup patch saved to ${backup_file}."
  return 0
}

update_repo() {
  local name="$1"
  local url="$2"
  local target="${UPSTREAM_DIR}/${name}"
  local before_head=""
  local after_head=""

  if [[ -d "${target}/.git" ]]; then
    echo "Updating ${name}..."

    if [[ -n "$(git -C "${target}" status --porcelain)" ]]; then
      if [[ "${name}" == "impeccable" ]]; then
        repair_impeccable_generated_dirty_state "${target}" || true
      fi
    fi

    if [[ -n "$(git -C "${target}" status --porcelain)" ]]; then
      echo "${name}: skipped because the upstream cache has local changes."
      record_repo_status "${name}" "skipped_dirty" "${before_head}" "${after_head}" "" "upstream cache has local changes"
      return 0
    fi

    before_head="$(git -C "${target}" rev-parse --short HEAD)"
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
    after_head="$(git -C "${target}" rev-parse --short HEAD)"

    if [[ "${before_head}" == "${after_head}" ]]; then
      echo "${name}: already up to date (${after_head})."
      record_repo_status "${name}" "up_to_date" "${before_head}" "${after_head}" "${default_branch}" "already up to date"
    else
      echo "${name}: ${before_head} -> ${after_head}."
      record_repo_status "${name}" "updated" "${before_head}" "${after_head}" "${default_branch}" "updated successfully"
    fi
  else
    echo "Cloning ${name}..."
    git clone "${url}" "${target}"
    after_head="$(git -C "${target}" rev-parse --short HEAD)"
    echo "${name}: installed at ${after_head}."
    record_repo_status "${name}" "installed" "" "${after_head}" "" "cloned successfully"
  fi
}

update_repo "superpowers" "https://github.com/obra/superpowers.git"
update_repo "dotclaude" "https://github.com/FradSer/dotclaude.git"
update_repo "impeccable" "https://github.com/pbakaus/impeccable.git"

if [[ "${BUILD_IMPECCABLE}" -eq 1 ]]; then
  bash "${ROOT_DIR}/scripts/build-impeccable-dist.sh"
  IMPECCABLE_BUILD_STATUS="built"
  IMPECCABLE_BUILD_MESSAGE="impeccable dist rebuilt"
else
  IMPECCABLE_BUILD_STATUS="skipped_by_flag"
  IMPECCABLE_BUILD_MESSAGE="impeccable build skipped by flag"
fi

if [[ -n "${REPORT_FILE}" ]]; then
  python3 - "${REPORT_FILE}" "${REPORT_LINES_FILE}" "${IMPECCABLE_BUILD_STATUS}" "${IMPECCABLE_BUILD_MESSAGE}" <<'PY'
import json
import sys

report_path, lines_path, build_status, build_message = sys.argv[1:]
repos = []

with open(lines_path, "r", encoding="utf-8") as handle:
    for raw_line in handle:
        name, status, before_commit, after_commit, default_branch, message = raw_line.rstrip("\n").split("\t")
        repos.append(
            {
                "name": name,
                "status": status,
                "before_commit": before_commit or None,
                "after_commit": after_commit or None,
                "default_branch": default_branch or None,
                "message": message or None,
            }
        )

payload = {
    "repositories": repos,
    "impeccable_build": {
        "status": build_status,
        "message": build_message,
    },
}

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY

  rm -f "${REPORT_LINES_FILE}"
fi
