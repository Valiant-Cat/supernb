#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib/install-common.sh"

TARGET_DIR="${1:-${PWD}}"
CLAUDE_DIR="${TARGET_DIR}/.claude"
IMPECCABLE_CLAUDE_DIR="${ROOT_DIR}/.supernb-cache/impeccable-dist/claude-code/.claude"
BUNDLED_SKILLS_DIR="${ROOT_DIR}/bundles/skills"
INSTALL_SCOPE_LABEL="project-local"

if [[ "${TARGET_DIR}" == "${HOME}" ]]; then
  INSTALL_SCOPE_LABEL="user-global"
fi

if [[ ! -d "${IMPECCABLE_CLAUDE_DIR}" ]]; then
  echo "Built impeccable Claude Code bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

mkdir -p "${CLAUDE_DIR}/skills"
echo "Installing Claude Code ${INSTALL_SCOPE_LABEL} assets into ${TARGET_DIR}:"
sync_directory_as_symlinks "${IMPECCABLE_CLAUDE_DIR}/skills" "${CLAUDE_DIR}/skills" ".claude/skills" "replace_skill_dir"
ensure_symlink_if_missing "${ROOT_DIR}/skills" "${CLAUDE_DIR}/skills/supernb" "supernb"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/sensortower-research" "${CLAUDE_DIR}/skills/sensortower-research" "sensortower-research"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/flutter-l10n-translation" "${CLAUDE_DIR}/skills/flutter-l10n-translation" "flutter-l10n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/android-i18n-translation" "${CLAUDE_DIR}/skills/android-i18n-translation" "android-i18n-translation"

superpowers_plugin_list() {
  (cd "${TARGET_DIR}" && claude plugin list 2>/dev/null || true)
}

superpowers_plugin_id_from_list() {
  local plugin_list="$1"
  printf '%s\n' "${plugin_list}" | grep -Eo 'superpowers@[^[:space:]]+' | head -n 1 || true
}

superpowers_plugin_status_from_list() {
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

install_default_superpowers_plugin() {
  if ! command -v claude >/dev/null 2>&1; then
    echo "  skipped plugin install: claude CLI not found"
    return 0
  fi

  local plugin_list
  local plugin_id
  local plugin_status

  plugin_list="$(superpowers_plugin_list)"
  plugin_id="$(superpowers_plugin_id_from_list "${plugin_list}")"

  if [[ -n "${plugin_id}" ]]; then
    plugin_status="$(superpowers_plugin_status_from_list "${plugin_list}" "${plugin_id}")"
    if [[ "${plugin_status}" == "disabled" ]]; then
      if (cd "${TARGET_DIR}" && claude plugin enable "${plugin_id}"); then
        echo "  enabled: Claude Code plugin ${plugin_id}"
      else
        echo "  installed but still disabled: Claude Code plugin ${plugin_id}"
      fi
      return 0
    fi

    echo "  already installed: Claude Code plugin ${plugin_id}"
    return 0
  fi

  if (cd "${TARGET_DIR}" && claude plugin install superpowers@claude-plugins-official); then
    echo "  installed: Claude Code plugin superpowers@claude-plugins-official"
    return 0
  fi

  echo "  official plugin install failed; trying marketplace fallback"
  if (cd "${TARGET_DIR}" && claude plugin marketplace add obra/superpowers-marketplace && claude plugin install superpowers@superpowers-marketplace); then
    echo "  installed: Claude Code plugin superpowers@superpowers-marketplace"
    return 0
  fi

  echo "  could not install Claude Code superpowers plugin automatically"
}

echo "Checking Claude Code plugin:"
install_default_superpowers_plugin

cat <<EOF
Installed Claude Code ${INSTALL_SCOPE_LABEL} assets into ${TARGET_DIR}

Default superpowers plugin is auto-installed when missing and auto-enabled when previously disabled.

Optional loop-oriented alternative:
  claude plugin marketplace add FradSer/dotclaude
  claude plugin install superpowers@frad-dotclaude

Do not use both same-named superpowers plugins side by side.

Restart Claude Code after bootstrap if the plugin was newly installed.
EOF
