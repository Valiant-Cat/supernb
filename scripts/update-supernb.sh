#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_SELF_UPDATE=0
SKIP_UPSTREAMS=0
SKIP_IMPECCABLE_BUILD=0
REPORT_DIR="${ROOT_DIR}/artifacts/updates"

usage() {
  cat <<'EOF'
Usage: ./scripts/update-supernb.sh [options]

Options:
  --skip-self-update       Do not fetch/pull the current supernb repository
  --skip-upstreams         Do not sync upstream repositories
  --skip-impeccable-build  Pass through to update-upstreams.sh
  --report-dir <path>      Where to write update reports. Default: artifacts/updates

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
    --report-dir)
      REPORT_DIR="${2:-}"
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
    SELF_STATUS="skipped_not_git"
    SELF_MESSAGE="current directory is not a git repository"
    echo "supernb self-update skipped: ${SELF_MESSAGE}."
    return 0
  fi

  before_head="$(git -C "${repo_dir}" rev-parse --short HEAD)"
  current_branch="$(git -C "${repo_dir}" branch --show-current)"
  SELF_BEFORE_COMMIT="${before_head}"
  SELF_BRANCH="${current_branch}"

  if [[ -n "$(git -C "${repo_dir}" status --porcelain)" ]]; then
    SELF_STATUS="skipped_dirty"
    SELF_MESSAGE="working tree is dirty"
    echo "supernb self-update skipped: ${SELF_MESSAGE}."
    return 0
  fi

  if ! git -C "${repo_dir}" fetch --all --prune; then
    SELF_STATUS="skipped_fetch_failed"
    SELF_MESSAGE="failed to fetch remote metadata"
    echo "supernb self-update skipped: ${SELF_MESSAGE}."
    return 0
  fi

  default_branch="$(determine_default_branch "${repo_dir}")" || {
    SELF_STATUS="skipped_no_default_branch"
    SELF_MESSAGE="could not determine default branch"
    echo "supernb self-update skipped: ${SELF_MESSAGE}."
    return 0
  }
  SELF_DEFAULT_BRANCH="${default_branch}"

  if [[ "${current_branch}" != "${default_branch}" ]]; then
    SELF_STATUS="skipped_non_default_branch"
    SELF_MESSAGE="current branch is ${current_branch}, default branch is ${default_branch}"
    echo "supernb self-update skipped: ${SELF_MESSAGE}."
    return 0
  fi

  git -C "${repo_dir}" pull --ff-only origin "${default_branch}"
  after_head="$(git -C "${repo_dir}" rev-parse --short HEAD)"
  SELF_AFTER_COMMIT="${after_head}"

  if [[ "${before_head}" == "${after_head}" ]]; then
    SELF_STATUS="up_to_date"
    SELF_MESSAGE="already up to date"
    echo "supernb self-update: already up to date (${after_head})."
  else
    SELF_STATUS="updated"
    SELF_MESSAGE="updated successfully"
    echo "supernb self-update: ${before_head} -> ${after_head}."
  fi
}

echo "Updating supernb..."

SELF_STATUS=""
SELF_MESSAGE=""
SELF_BEFORE_COMMIT=""
SELF_AFTER_COMMIT=""
SELF_BRANCH=""
SELF_DEFAULT_BRANCH=""

if [[ "${SKIP_SELF_UPDATE}" -eq 0 ]]; then
  update_self_repo "${ROOT_DIR}"
else
  SELF_STATUS="skipped_by_flag"
  SELF_MESSAGE="self-update skipped by flag"
  echo "supernb self-update skipped by flag."
fi

UPSTREAM_REPORT_FILE="$(mktemp)"

if [[ "${SKIP_UPSTREAMS}" -eq 0 ]]; then
  upstream_args=()
  if [[ "${SKIP_IMPECCABLE_BUILD}" -eq 1 ]]; then
    upstream_args+=(--skip-impeccable-build)
  fi
  upstream_args+=(--report-file "${UPSTREAM_REPORT_FILE}")
  bash "${ROOT_DIR}/scripts/update-upstreams.sh" "${upstream_args[@]}"
else
  python3 - "${UPSTREAM_REPORT_FILE}" <<'PY'
import json
import sys

payload = {
    "repositories": [],
    "impeccable_build": {
        "status": "skipped_by_flag",
        "message": "upstream sync skipped by flag",
    },
}

with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
  echo "upstream sync skipped by flag."
fi

SELF_REPORT_FILE="$(mktemp)"
python3 - "${SELF_REPORT_FILE}" "${SELF_STATUS}" "${SELF_MESSAGE}" "${SELF_BEFORE_COMMIT}" "${SELF_AFTER_COMMIT}" "${SELF_BRANCH}" "${SELF_DEFAULT_BRANCH}" <<'PY'
import json
import sys

report_path, status, message, before_commit, after_commit, branch, default_branch = sys.argv[1:]
payload = {
    "status": status,
    "message": message,
    "before_commit": before_commit or None,
    "after_commit": after_commit or None,
    "branch": branch or None,
    "default_branch": default_branch or None,
}

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY

REPORT_TIMESTAMP="$(date '+%Y-%m-%dT%H:%M:%S%z')"
REPORT_OUTPUT="$(python3 "${ROOT_DIR}/scripts/write-update-report.py" "${REPORT_DIR}" "${REPORT_TIMESTAMP}" "${ROOT_DIR}" "${SELF_REPORT_FILE}" "${UPSTREAM_REPORT_FILE}")"
REPORT_JSON_PATH="$(python3 - "${REPORT_OUTPUT}" <<'PY'
import json
import sys
print(json.loads(sys.argv[1])["json"])
PY
)"
REPORT_MARKDOWN_PATH="$(python3 - "${REPORT_OUTPUT}" <<'PY'
import json
import sys
print(json.loads(sys.argv[1])["markdown"])
PY
)"

rm -f "${SELF_REPORT_FILE}" "${UPSTREAM_REPORT_FILE}"

echo "Update report written:"
echo "  JSON: ${REPORT_JSON_PATH}"
echo "  Markdown: ${REPORT_MARKDOWN_PATH}"
