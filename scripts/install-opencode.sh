#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib/install-common.sh"

TARGET_DIR="${1:-${PWD}}"
OPENCODE_DIR="${TARGET_DIR}/.opencode"
IMPECCABLE_OPENCODE_DIR="${ROOT_DIR}/.supernb-cache/impeccable-dist/opencode/.opencode"
BUNDLED_SKILLS_DIR="${ROOT_DIR}/bundles/skills"
OPENCODE_CONFIG="${TARGET_DIR}/opencode.json"
SUPERS_PLUGIN="superpowers@git+https://github.com/obra/superpowers.git"

if [[ ! -d "${IMPECCABLE_OPENCODE_DIR}" ]]; then
  echo "Built impeccable OpenCode bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

mkdir -p "${OPENCODE_DIR}/skills"
echo "Installing OpenCode project assets into ${TARGET_DIR}:"
sync_directory_as_symlinks "${IMPECCABLE_OPENCODE_DIR}/skills" "${OPENCODE_DIR}/skills" ".opencode/skills" "replace_skill_dir"
remove_managed_symlink_if_target_matches "${OPENCODE_DIR}/skills/supernb" "${ROOT_DIR}/skills" "supernb"
sync_directory_as_symlinks "${ROOT_DIR}/skills" "${OPENCODE_DIR}/skills" "supernb" "replace_skill_dir"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/sensortower-research" "${OPENCODE_DIR}/skills/sensortower-research" "sensortower-research"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/flutter-l10n-translation" "${OPENCODE_DIR}/skills/flutter-l10n-translation" "flutter-l10n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/android-i18n-translation" "${OPENCODE_DIR}/skills/android-i18n-translation" "android-i18n-translation"

python3 "${ROOT_DIR}/scripts/ensure-opencode-plugin.py" "${OPENCODE_CONFIG}" "${SUPERS_PLUGIN}"

cat <<EOF
Installed project-local assets into ${TARGET_DIR}

Ensured this plugin entry in ${OPENCODE_CONFIG}:
  ${SUPERS_PLUGIN}

Restart OpenCode after saving the config.
EOF
