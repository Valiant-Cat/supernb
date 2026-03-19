#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_SKILLS_DIR="${HOME}/.agents/skills"
IMPECCABLE_SKILLS_DIR="${ROOT_DIR}/upstreams/impeccable/dist/codex/.codex/skills"
SENSORTOWER_SKILL_DIR="/Users/xiaomiao26_1_26/.codex/skills/sensortower-research"

mkdir -p "${AGENTS_SKILLS_DIR}"

if [[ ! -d "${ROOT_DIR}/upstreams/superpowers/skills" ]]; then
  echo "superpowers skills not found. Run ./scripts/update-upstreams.sh first." >&2
  exit 1
fi

if [[ ! -d "${IMPECCABLE_SKILLS_DIR}" ]]; then
  echo "Built impeccable Codex bundle not found. Run ./scripts/build-impeccable-dist.sh first." >&2
  exit 1
fi

if [[ ! -d "${SENSORTOWER_SKILL_DIR}" ]]; then
  echo "Local sensortower skill not found at ${SENSORTOWER_SKILL_DIR}" >&2
  exit 1
fi

ln -sfn "${ROOT_DIR}/skills" "${AGENTS_SKILLS_DIR}/supernb"
ln -sfn "${ROOT_DIR}/upstreams/superpowers/skills" "${AGENTS_SKILLS_DIR}/superpowers"
ln -sfn "${IMPECCABLE_SKILLS_DIR}" "${AGENTS_SKILLS_DIR}/impeccable"
ln -sfn "${SENSORTOWER_SKILL_DIR}" "${AGENTS_SKILLS_DIR}/sensortower-research"

cat <<EOF
Installed Codex skill links:
  ${AGENTS_SKILLS_DIR}/supernb
  ${AGENTS_SKILLS_DIR}/superpowers
  ${AGENTS_SKILLS_DIR}/impeccable
  ${AGENTS_SKILLS_DIR}/sensortower-research

Restart Codex to pick up the new skills.
EOF

