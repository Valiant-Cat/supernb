#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="${ROOT_DIR}/templates"
SUPERNB_CLI="${ROOT_DIR}/scripts/supernb"
DATE_STAMP="$(date +%F)"
GOAL="${GOAL:-}"
REPOSITORY="${REPOSITORY:-}"
PROJECT_DIR="${PROJECT_DIR:-}"
HARNESS="${HARNESS:-}"
PLATFORM="${PLATFORM:-}"
STACK="${STACK:-}"
PRODUCT_CATEGORY="${PRODUCT_CATEGORY:-}"
MARKETS="${MARKETS:-}"
RESEARCH_WINDOW="${RESEARCH_WINDOW:-}"
SEED_COMPETITORS="${SEED_COMPETITORS:-}"
SOURCE_LOCALE="${SOURCE_LOCALE:-en}"
TARGET_LOCALES="${TARGET_LOCALES:-}"
SCALE_TARGET_DAU="${SCALE_TARGET_DAU:-10000000}"
QUALITY_BAR="${QUALITY_BAR:-10m-dau-grade}"
CONSTRAINTS="${CONSTRAINTS:-}"

resolve_dir() {
  local target="$1"
  if [[ ! -d "${target}" ]]; then
    echo "Directory not found: ${target}" >&2
    exit 1
  fi
  (cd "${target}" && pwd -P)
}

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/init-initiative.sh <initiative-slug> [title]" >&2
  exit 1
fi

RAW_SLUG="$1"
TITLE="${2:-$1}"
SLUG="$(printf '%s' "${RAW_SLUG}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"

if [[ -z "${SLUG}" ]]; then
  echo "Initiative slug resolved to empty value." >&2
  exit 1
fi

INIT_ID="${DATE_STAMP}-${SLUG}"
if [[ -n "${PROJECT_DIR}" ]]; then
  PRODUCT_ROOT="$(resolve_dir "${PROJECT_DIR}")"
elif [[ -n "${REPOSITORY}" && -d "${REPOSITORY}" ]]; then
  PRODUCT_ROOT="$(resolve_dir "${REPOSITORY}")"
elif [[ "$(pwd -P)" != "${ROOT_DIR}" ]]; then
  PRODUCT_ROOT="$(pwd -P)"
else
  PRODUCT_ROOT="${ROOT_DIR}"
fi

PROJECT_DIR="${PRODUCT_ROOT}"
ARTIFACTS_ROOT="${PRODUCT_ROOT}/.supernb"
RESEARCH_DIR="${ARTIFACTS_ROOT}/research/${INIT_ID}"
PRD_DIR="${ARTIFACTS_ROOT}/prd/${INIT_ID}"
DESIGN_DIR="${ARTIFACTS_ROOT}/design/${INIT_ID}"
PLANS_DIR="${ARTIFACTS_ROOT}/plans/${INIT_ID}"
RELEASE_DIR="${ARTIFACTS_ROOT}/releases/${INIT_ID}"
INDEX_DIR="${ARTIFACTS_ROOT}/initiatives"
INITIATIVE_DIR="${INDEX_DIR}/${INIT_ID}"
INDEX_FILE="${INDEX_DIR}/${INIT_ID}.md"
SPEC_FILE="${INITIATIVE_DIR}/initiative.yaml"
RUN_STATUS_FILE="${INITIATIVE_DIR}/run-status.md"
CERTIFICATION_STATE_FILE="${INITIATIVE_DIR}/certification-state.json"
NEXT_COMMAND_FILE="${INITIATIVE_DIR}/next-command.md"
PHASE_PACKET_FILE="${INITIATIVE_DIR}/phase-packet.md"
RUN_LOG_FILE="${INITIATIVE_DIR}/run-log.md"
COMMAND_BRIEFS_DIR="${INITIATIVE_DIR}/command-briefs"
PHASE_RESULTS_DIR="${INITIATIVE_DIR}/phase-results"
EXECUTIONS_DIR="${INITIATIVE_DIR}/executions"
LOCATOR_DIR="${ROOT_DIR}/artifacts/initiative-locations"
LOCATOR_FILE="${LOCATOR_DIR}/${INIT_ID}.txt"

mkdir -p "${RESEARCH_DIR}" "${PRD_DIR}" "${DESIGN_DIR}" "${PLANS_DIR}" "${RELEASE_DIR}" "${INDEX_DIR}" "${INITIATIVE_DIR}" "${COMMAND_BRIEFS_DIR}" "${PHASE_RESULTS_DIR}" "${EXECUTIONS_DIR}" "${LOCATOR_DIR}"
printf '%s\n' "${SPEC_FILE}" > "${LOCATOR_FILE}"

yaml_escape() {
  printf '%s' "$1" | perl -0pe 's/\\/\\\\/g; s/"/\\"/g; s/\n/\\n/g'
}

render_template() {
  local template_path="$1"
  local output_path="$2"

  perl -0pe '
    s/\{\{INIT_ID\}\}/$ENV{INIT_ID}/g;
    s/\{\{DATE_STAMP\}\}/$ENV{DATE_STAMP}/g;
    s/\{\{SLUG\}\}/$ENV{SLUG}/g;
    s/\{\{TITLE\}\}/$ENV{TITLE}/g;
    s/\{\{GOAL_YAML\}\}/$ENV{GOAL_YAML}/g;
    s/\{\{REPOSITORY_YAML\}\}/$ENV{REPOSITORY_YAML}/g;
    s/\{\{PROJECT_DIR_YAML\}\}/$ENV{PROJECT_DIR_YAML}/g;
    s/\{\{HARNESS_YAML\}\}/$ENV{HARNESS_YAML}/g;
    s/\{\{PLATFORM_YAML\}\}/$ENV{PLATFORM_YAML}/g;
    s/\{\{STACK_YAML\}\}/$ENV{STACK_YAML}/g;
    s/\{\{PRODUCT_CATEGORY_YAML\}\}/$ENV{PRODUCT_CATEGORY_YAML}/g;
    s/\{\{MARKETS_YAML\}\}/$ENV{MARKETS_YAML}/g;
    s/\{\{RESEARCH_WINDOW_YAML\}\}/$ENV{RESEARCH_WINDOW_YAML}/g;
    s/\{\{SEED_COMPETITORS_YAML\}\}/$ENV{SEED_COMPETITORS_YAML}/g;
    s/\{\{SOURCE_LOCALE_YAML\}\}/$ENV{SOURCE_LOCALE_YAML}/g;
    s/\{\{TARGET_LOCALES_YAML\}\}/$ENV{TARGET_LOCALES_YAML}/g;
    s/\{\{SCALE_TARGET_DAU_YAML\}\}/$ENV{SCALE_TARGET_DAU_YAML}/g;
    s/\{\{QUALITY_BAR_YAML\}\}/$ENV{QUALITY_BAR_YAML}/g;
    s/\{\{CONSTRAINTS_YAML\}\}/$ENV{CONSTRAINTS_YAML}/g;
    s/\{\{SUPERNB_CLI\}\}/$ENV{SUPERNB_CLI}/g;
  ' "${template_path}" > "${output_path}"
}

export INIT_ID DATE_STAMP SLUG TITLE SUPERNB_CLI
export GOAL_YAML="$(yaml_escape "${GOAL}")"
export REPOSITORY_YAML="$(yaml_escape "${REPOSITORY}")"
export PROJECT_DIR_YAML="$(yaml_escape "${PROJECT_DIR}")"
export HARNESS_YAML="$(yaml_escape "${HARNESS}")"
export PLATFORM_YAML="$(yaml_escape "${PLATFORM}")"
export STACK_YAML="$(yaml_escape "${STACK}")"
export PRODUCT_CATEGORY_YAML="$(yaml_escape "${PRODUCT_CATEGORY}")"
export MARKETS_YAML="$(yaml_escape "${MARKETS}")"
export RESEARCH_WINDOW_YAML="$(yaml_escape "${RESEARCH_WINDOW}")"
export SEED_COMPETITORS_YAML="$(yaml_escape "${SEED_COMPETITORS}")"
export SOURCE_LOCALE_YAML="$(yaml_escape "${SOURCE_LOCALE}")"
export TARGET_LOCALES_YAML="$(yaml_escape "${TARGET_LOCALES}")"
export SCALE_TARGET_DAU_YAML="$(yaml_escape "${SCALE_TARGET_DAU}")"
export QUALITY_BAR_YAML="$(yaml_escape "${QUALITY_BAR}")"
export CONSTRAINTS_YAML="$(yaml_escape "${CONSTRAINTS}")"

render_template "${TEMPLATES_DIR}/initiative-index.md" "${INDEX_FILE}"
render_template "${TEMPLATES_DIR}/initiative-spec.yaml" "${SPEC_FILE}"
render_template "${TEMPLATES_DIR}/research/01-competitor-landscape.md" "${RESEARCH_DIR}/01-competitor-landscape.md"
render_template "${TEMPLATES_DIR}/research/02-review-insights.md" "${RESEARCH_DIR}/02-review-insights.md"
render_template "${TEMPLATES_DIR}/research/03-feature-opportunities.md" "${RESEARCH_DIR}/03-feature-opportunities.md"
render_template "${TEMPLATES_DIR}/prd/product-requirements.md" "${PRD_DIR}/product-requirements.md"
render_template "${TEMPLATES_DIR}/design/ui-ux-spec.md" "${DESIGN_DIR}/ui-ux-spec.md"
render_template "${TEMPLATES_DIR}/design/i18n-strategy.md" "${DESIGN_DIR}/i18n-strategy.md"
render_template "${TEMPLATES_DIR}/plans/implementation-plan.md" "${PLANS_DIR}/implementation-plan.md"
render_template "${TEMPLATES_DIR}/releases/release-readiness.md" "${RELEASE_DIR}/release-readiness.md"

cat > "${RUN_STATUS_FILE}" <<EOF
# Run Status

- Initiative ID: \`${INIT_ID}\`
- Current state: not evaluated

Run:

\`\`\`bash
"${SUPERNB_CLI}" run --initiative-id ${INIT_ID}
\`\`\`
EOF

cat > "${CERTIFICATION_STATE_FILE}" <<EOF
{
  "initiative_id": "${INIT_ID}",
  "phases": {}
}
EOF

cat > "${NEXT_COMMAND_FILE}" <<EOF
# Next Command

Run \`"${SUPERNB_CLI}" run --initiative-id ${INIT_ID}\` to generate the next structured command brief for this initiative.
EOF

cat > "${PHASE_PACKET_FILE}" <<EOF
# Phase Packet

Run \`"${SUPERNB_CLI}" run --initiative-id ${INIT_ID}\` to generate the current phase execution packet.
EOF

cat > "${RUN_LOG_FILE}" <<EOF
# Run Log

This file records each \`supernb run\` evaluation for \`${INIT_ID}\`.
EOF

cat <<EOF
Initialized initiative scaffold: ${INIT_ID}
Product workspace: ${PRODUCT_ROOT}
Initiative root: ${ARTIFACTS_ROOT}

Created:
  ${INDEX_FILE}
  ${SPEC_FILE}
  ${RUN_STATUS_FILE}
  ${CERTIFICATION_STATE_FILE}
  ${NEXT_COMMAND_FILE}
  ${PHASE_PACKET_FILE}
  ${RUN_LOG_FILE}
  ${COMMAND_BRIEFS_DIR}
  ${PHASE_RESULTS_DIR}
  ${EXECUTIONS_DIR}
  ${RESEARCH_DIR}/01-competitor-landscape.md
  ${RESEARCH_DIR}/02-review-insights.md
  ${RESEARCH_DIR}/03-feature-opportunities.md
  ${PRD_DIR}/product-requirements.md
  ${DESIGN_DIR}/ui-ux-spec.md
  ${DESIGN_DIR}/i18n-strategy.md
  ${PLANS_DIR}/implementation-plan.md
  ${RELEASE_DIR}/release-readiness.md
  ${LOCATOR_FILE}

Recommended next step:
  Run "${SUPERNB_CLI}" run --initiative-id ${INIT_ID}
EOF
