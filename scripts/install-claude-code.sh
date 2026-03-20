#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib/install-common.sh"

TARGET_DIR="${1:-${PWD}}"
CLAUDE_DIR="${TARGET_DIR}/.claude"
IMPECCABLE_CLAUDE_DIR="${ROOT_DIR}/.supernb-cache/impeccable-dist/claude-code/.claude"
BUNDLED_SKILLS_DIR="${ROOT_DIR}/bundles/skills"
RALPH_LOOP_MARKETPLACE_DIR="${ROOT_DIR}/bundles/claude-loop-marketplace"
RALPH_LOOP_PLUGIN_ID="supernb-loop@supernb"
PROJECT_INSTRUCTIONS_TEMPLATE="${ROOT_DIR}/templates/claude/supernb-project-instructions.md"
USER_INSTRUCTIONS_TEMPLATE="${ROOT_DIR}/templates/claude/supernb-user-instructions.md"
INSTALL_SCOPE_LABEL="project-local"
CLAUDE_INSTRUCTIONS_TEMPLATE="${PROJECT_INSTRUCTIONS_TEMPLATE}"
CLAUDE_MD_PATH="${TARGET_DIR}/CLAUDE.md"
MANAGED_BLOCK_START="<!-- SUPERNB:START -->"
MANAGED_BLOCK_END="<!-- SUPERNB:END -->"

if [[ "${TARGET_DIR}" == "${HOME}" ]]; then
  INSTALL_SCOPE_LABEL="user-global"
  CLAUDE_INSTRUCTIONS_TEMPLATE="${USER_INSTRUCTIONS_TEMPLATE}"
  CLAUDE_MD_PATH="${CLAUDE_DIR}/CLAUDE.md"
fi

if [[ ! -d "${IMPECCABLE_CLAUDE_DIR}" ]]; then
  echo "Built impeccable Claude Code bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

ensure_managed_claude_md_block() {
  if [[ ! -f "${CLAUDE_INSTRUCTIONS_TEMPLATE}" ]]; then
    echo "  skipped CLAUDE.md managed block: template missing"
    return 0
  fi

  local managed_block
  local rendered_template
  mkdir -p "$(dirname "${CLAUDE_MD_PATH}")"
  rendered_template="$(CLAUDE_INSTRUCTIONS_TEMPLATE="${CLAUDE_INSTRUCTIONS_TEMPLATE}" ROOT_DIR="${ROOT_DIR}" python3 - <<'PY'
from pathlib import Path
import os

template_path = Path(os.environ["CLAUDE_INSTRUCTIONS_TEMPLATE"])
root_dir = os.environ["ROOT_DIR"]
text = template_path.read_text(encoding="utf-8")
print(text.replace("{{SUPERNB_ROOT}}", root_dir), end="")
PY
)"
  managed_block="$(cat <<EOF
${MANAGED_BLOCK_START}
${rendered_template}
${MANAGED_BLOCK_END}
EOF
)"

  if [[ ! -f "${CLAUDE_MD_PATH}" ]]; then
    printf '%s\n' "${managed_block}" > "${CLAUDE_MD_PATH}"
    echo "  installed: $(basename "${CLAUDE_MD_PATH}") managed supernb instructions"
    return 0
  fi

  local existing
  existing="$(cat "${CLAUDE_MD_PATH}")"
  if grep -Fq "${MANAGED_BLOCK_START}" "${CLAUDE_MD_PATH}" && grep -Fq "${MANAGED_BLOCK_END}" "${CLAUDE_MD_PATH}"; then
    CLAUDE_MD_PATH="${CLAUDE_MD_PATH}" MANAGED_BLOCK_START="${MANAGED_BLOCK_START}" MANAGED_BLOCK_END="${MANAGED_BLOCK_END}" MANAGED_BLOCK="${managed_block}" python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["CLAUDE_MD_PATH"])
start = os.environ["MANAGED_BLOCK_START"]
end = os.environ["MANAGED_BLOCK_END"]
managed = os.environ["MANAGED_BLOCK"]
text = path.read_text(encoding="utf-8")
start_idx = text.index(start)
end_idx = text.index(end, start_idx) + len(end)
replacement = managed
if start_idx > 0 and text[start_idx - 1] != "\n":
    replacement = "\n" + replacement
if end_idx < len(text) and text[end_idx:end_idx + 1] != "\n":
    replacement = replacement + "\n"
path.write_text(text[:start_idx] + replacement + text[end_idx:], encoding="utf-8")
PY
    echo "  updated: $(basename "${CLAUDE_MD_PATH}") managed supernb instructions"
    return 0
  fi

  printf '\n\n%s\n' "${managed_block}" >> "${CLAUDE_MD_PATH}"
  echo "  appended: $(basename "${CLAUDE_MD_PATH}") managed supernb instructions"
}

mkdir -p "${CLAUDE_DIR}/skills"
echo "Installing Claude Code ${INSTALL_SCOPE_LABEL} assets into ${TARGET_DIR}:"
sync_directory_as_symlinks "${IMPECCABLE_CLAUDE_DIR}/skills" "${CLAUDE_DIR}/skills" ".claude/skills" "replace_skill_dir"
remove_managed_symlink_if_target_matches "${CLAUDE_DIR}/skills/supernb" "${ROOT_DIR}/skills" "supernb"
sync_directory_as_symlinks "${ROOT_DIR}/skills" "${CLAUDE_DIR}/skills" "supernb" "replace_skill_dir"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/sensortower-research" "${CLAUDE_DIR}/skills/sensortower-research" "sensortower-research"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/flutter-l10n-translation" "${CLAUDE_DIR}/skills/flutter-l10n-translation" "flutter-l10n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/android-i18n-translation" "${CLAUDE_DIR}/skills/android-i18n-translation" "android-i18n-translation"
ensure_managed_claude_md_block

claude_plugin_list() {
  (cd "${TARGET_DIR}" && claude plugin list 2>/dev/null || true)
}

claude_plugin_id_from_list() {
  local plugin_list="$1"
  printf '%s\n' "${plugin_list}" | grep -Eo '[A-Za-z0-9_.-]+@[^[:space:]]+' | head -n 1 || true
}

claude_plugin_status_from_list() {
  local plugin_list="$1"
  local plugin_id="$2"
  local status_line

  status_line="$(printf '%s\n' "${plugin_list}" | grep -F -A3 "${plugin_id}" | grep -F 'Status:' | head -n 1 || true)"
  if [[ "${status_line}" == *"disabled"* ]]; then
    echo "disabled"
    return 0
  fi
  if [[ "${status_line}" == *"enabled"* ]]; then
    echo "enabled"
    return 0
  fi
  echo "unknown"
}

install_supernb_loop_plugin() {
  if ! command -v claude >/dev/null 2>&1; then
    echo "  skipped plugin install: claude CLI not found"
    return 0
  fi

  if [[ ! -d "${RALPH_LOOP_MARKETPLACE_DIR}" ]]; then
    echo "  failed: bundled supernb Claude loop marketplace not found at ${RALPH_LOOP_MARKETPLACE_DIR}" >&2
    exit 1
  fi

  local install_scope="project"
  local plugin_list
  local plugin_id
  local plugin_status

  if [[ "${INSTALL_SCOPE_LABEL}" == "user-global" ]]; then
    install_scope="user"
  fi

  (cd "${TARGET_DIR}" && claude plugin marketplace add "${RALPH_LOOP_MARKETPLACE_DIR}" --scope "${install_scope}" >/dev/null 2>&1 || true)

  plugin_list="$(claude_plugin_list)"
  plugin_status="$(claude_plugin_status_from_list "${plugin_list}" "${RALPH_LOOP_PLUGIN_ID}")"
  if [[ "${plugin_status}" == "enabled" ]]; then
    echo "  already enabled: Claude Code plugin ${RALPH_LOOP_PLUGIN_ID}"
    return 0
  fi

  if [[ "${plugin_status}" == "disabled" ]]; then
    if (cd "${TARGET_DIR}" && claude plugin enable "${RALPH_LOOP_PLUGIN_ID}" --scope "${install_scope}" >/dev/null 2>&1); then
      echo "  enabled: Claude Code plugin ${RALPH_LOOP_PLUGIN_ID}"
      return 0
    fi
  fi

  if (cd "${TARGET_DIR}" && claude plugin install "${RALPH_LOOP_PLUGIN_ID}" --scope "${install_scope}" >/dev/null 2>&1); then
    echo "  installed: Claude Code plugin ${RALPH_LOOP_PLUGIN_ID}"
    return 0
  fi

  echo "  failed: could not install or enable ${RALPH_LOOP_PLUGIN_ID} in ${install_scope} scope" >&2
  exit 1
}

echo "Checking Claude Code plugin:"
install_supernb_loop_plugin

cat <<EOF
Installed Claude Code ${INSTALL_SCOPE_LABEL} assets into ${TARGET_DIR}

User-global installs now maintain ~/.claude/CLAUDE.md and configure the bundled supernb loop plugin so simple prompts like:
  use supernb to improve this project
work across projects without restating the full workflow.

Project-local installs also maintain a managed CLAUDE.md block so simple prompts like:
  use supernb to improve this project
still route through the full supernb prompt-first workflow.

The managed Ralph Loop provider is the bundled `supernb-loop@supernb` plugin from:
  ${RALPH_LOOP_MARKETPLACE_DIR}

Use that managed Claude Code environment for prompt-first planning or delivery sessions that must not self-terminate.

Restart Claude Code after bootstrap if the plugin was newly installed.
EOF
