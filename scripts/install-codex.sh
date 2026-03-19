#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_SKILLS_DIR="${HOME}/.agents/skills"
IMPECCABLE_SKILLS_DIR="${ROOT_DIR}/upstreams/impeccable/dist/codex/.codex/skills"
SENSORTOWER_SKILL_DIR="/Users/xiaomiao26_1_26/.codex/skills/sensortower-research"
FLUTTER_L10N_SKILL_DIR="/Users/xiaomiao26_1_26/.codex/skills/flutter-l10n-translation"
ANDROID_I18N_SKILL_DIR="/Users/xiaomiao26_1_26/.codex/skills/android-i18n-translation"

mkdir -p "${AGENTS_SKILLS_DIR}"

if [[ ! -d "${ROOT_DIR}/upstreams/superpowers/skills" ]]; then
  echo "superpowers skills not found. Run ./scripts/update-upstreams.sh first." >&2
  exit 1
fi

if [[ ! -d "${IMPECCABLE_SKILLS_DIR}" ]]; then
  echo "Built impeccable Codex bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

ln -sfn "${ROOT_DIR}/skills" "${AGENTS_SKILLS_DIR}/supernb"
ln -sfn "${ROOT_DIR}/upstreams/superpowers/skills" "${AGENTS_SKILLS_DIR}/superpowers"
ln -sfn "${IMPECCABLE_SKILLS_DIR}" "${AGENTS_SKILLS_DIR}/impeccable"

link_optional_skill() {
  local source_dir="$1"
  local link_name="$2"

  if [[ -d "${source_dir}" ]]; then
    ln -sfn "${source_dir}" "${AGENTS_SKILLS_DIR}/${link_name}"
    echo "  ${AGENTS_SKILLS_DIR}/${link_name}"
  else
    echo "  skipped optional skill: ${link_name} (${source_dir} not found)"
  fi
}

cat <<EOF
Installed Codex skill links:
  ${AGENTS_SKILLS_DIR}/supernb
  ${AGENTS_SKILLS_DIR}/superpowers
  ${AGENTS_SKILLS_DIR}/impeccable
EOF

echo "Optional local skill links:"
link_optional_skill "${SENSORTOWER_SKILL_DIR}" "sensortower-research"
link_optional_skill "${FLUTTER_L10N_SKILL_DIR}" "flutter-l10n-translation"
link_optional_skill "${ANDROID_I18N_SKILL_DIR}" "android-i18n-translation"

echo
echo "Restart Codex to pick up the new skills."
