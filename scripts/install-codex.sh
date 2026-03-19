#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/lib/install-common.sh"

AGENTS_SKILLS_DIR="${HOME}/.agents/skills"
IMPECCABLE_SKILLS_DIR="${ROOT_DIR}/upstreams/impeccable/dist/codex/.codex/skills"
BUNDLED_SKILLS_DIR="${ROOT_DIR}/bundles/skills"

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
ensure_symlink_if_missing "${ROOT_DIR}/skills" "${AGENTS_SKILLS_DIR}/supernb" "supernb"
ensure_symlink_if_missing "${ROOT_DIR}/upstreams/superpowers/skills" "${AGENTS_SKILLS_DIR}/superpowers" "superpowers"
ensure_symlink_if_missing "${IMPECCABLE_SKILLS_DIR}" "${AGENTS_SKILLS_DIR}/impeccable" "impeccable"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/sensortower-research" "${AGENTS_SKILLS_DIR}/sensortower-research" "sensortower-research"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/flutter-l10n-translation" "${AGENTS_SKILLS_DIR}/flutter-l10n-translation" "flutter-l10n-translation"
ensure_symlink_if_missing "${BUNDLED_SKILLS_DIR}/android-i18n-translation" "${AGENTS_SKILLS_DIR}/android-i18n-translation" "android-i18n-translation"

echo
echo "Restart Codex to pick up the new skills."
