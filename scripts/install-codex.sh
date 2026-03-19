#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib/install-common.sh"

AGENTS_SKILLS_DIR="${HOME}/.agents/skills"
IMPECCABLE_SKILLS_DIR="${ROOT_DIR}/.supernb-cache/impeccable-dist/codex/.codex/skills"
BUNDLED_SKILLS_DIR="${ROOT_DIR}/bundles/skills"
LEGACY_IMPECCABLE_SKILLS_DIR="${ROOT_DIR}/upstreams/impeccable/dist/codex/.codex/skills"

mkdir -p "${AGENTS_SKILLS_DIR}"

if [[ ! -d "${ROOT_DIR}/upstreams/superpowers/skills" ]]; then
  echo "superpowers skills not found. Run ./scripts/update-upstreams.sh first." >&2
  exit 1
fi

if [[ ! -d "${IMPECCABLE_SKILLS_DIR}" ]]; then
  echo "Built impeccable Codex bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

echo "Installing Codex skills into ${AGENTS_SKILLS_DIR}:"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/supernb" "${ROOT_DIR}/skills" "supernb"
sync_directory_as_symlinks "${ROOT_DIR}/skills" "${AGENTS_SKILLS_DIR}" "supernb" "replace_skill_dir"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/superpowers" "${ROOT_DIR}/upstreams/superpowers/skills" "superpowers"
sync_directory_as_symlinks "${ROOT_DIR}/upstreams/superpowers/skills" "${AGENTS_SKILLS_DIR}" "superpowers" "replace_skill_dir"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/impeccable" "${IMPECCABLE_SKILLS_DIR}" "impeccable"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/impeccable" "${LEGACY_IMPECCABLE_SKILLS_DIR}" "impeccable"
sync_directory_as_symlinks "${IMPECCABLE_SKILLS_DIR}" "${AGENTS_SKILLS_DIR}" "impeccable" "replace_skill_dir"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/sensortower-research" "${HOME}/.codex/skills/sensortower-research" "sensortower-research"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/flutter-l10n-translation" "${HOME}/.codex/skills/flutter-l10n-translation" "flutter-l10n-translation"
remove_managed_symlink_if_target_matches "${AGENTS_SKILLS_DIR}/android-i18n-translation" "${HOME}/.codex/skills/android-i18n-translation" "android-i18n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/sensortower-research" "${AGENTS_SKILLS_DIR}/sensortower-research" "sensortower-research"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/flutter-l10n-translation" "${AGENTS_SKILLS_DIR}/flutter-l10n-translation" "flutter-l10n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/android-i18n-translation" "${AGENTS_SKILLS_DIR}/android-i18n-translation" "android-i18n-translation"

echo
echo "Restart Codex to pick up the new skills."
