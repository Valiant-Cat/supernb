#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib/install-common.sh"

TARGET_DIR="${1:-${ROOT_DIR}}"
CLAUDE_DIR="${TARGET_DIR}/.claude"
IMPECCABLE_CLAUDE_DIR="${ROOT_DIR}/upstreams/impeccable/dist/claude-code/.claude"
BUNDLED_SKILLS_DIR="${ROOT_DIR}/bundles/skills"

if [[ ! -d "${IMPECCABLE_CLAUDE_DIR}" ]]; then
  echo "Built impeccable Claude Code bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

mkdir -p "${CLAUDE_DIR}/skills"
echo "Installing Claude Code project assets into ${TARGET_DIR}:"
copy_tree_contents_if_missing "${IMPECCABLE_CLAUDE_DIR}/skills" "${CLAUDE_DIR}/skills" ".claude/skills"
ensure_symlink_if_missing "${ROOT_DIR}/skills" "${CLAUDE_DIR}/skills/supernb" "supernb"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/sensortower-research" "${CLAUDE_DIR}/skills/sensortower-research" "sensortower-research"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/flutter-l10n-translation" "${CLAUDE_DIR}/skills/flutter-l10n-translation" "flutter-l10n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/android-i18n-translation" "${CLAUDE_DIR}/skills/android-i18n-translation" "android-i18n-translation"

install_default_superpowers_plugin() {
  if ! command -v claude >/dev/null 2>&1; then
    echo "  skipped plugin install: claude CLI not found"
    return 0
  fi

  if (cd "${TARGET_DIR}" && claude plugin list 2>/dev/null | grep -Eq '(^|[[:space:]])superpowers@'); then
    echo "  already installed: Claude Code plugin superpowers"
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
Installed project-local assets into ${TARGET_DIR}

Default superpowers plugin is auto-installed when missing.

Optional loop-oriented alternative:
  claude plugin marketplace add FradSer/dotclaude
  claude plugin install superpowers@frad-dotclaude

Do not use both same-named superpowers plugins side by side.

Restart Claude Code after bootstrap if the plugin was newly installed.
EOF
