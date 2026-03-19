#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="${ROOT_DIR}/templates"
DATE_STAMP="$(date +%F)"
GOAL="${GOAL:-}"
REPOSITORY="${REPOSITORY:-}"
PLATFORM="${PLATFORM:-}"
STACK="${STACK:-}"
PRODUCT_CATEGORY="${PRODUCT_CATEGORY:-}"
MARKETS="${MARKETS:-}"
RESEARCH_WINDOW="${RESEARCH_WINDOW:-}"
SEED_COMPETITORS="${SEED_COMPETITORS:-}"
SOURCE_LOCALE="${SOURCE_LOCALE:-en}"
TARGET_LOCALES="${TARGET_LOCALES:-}"
QUALITY_BAR="${QUALITY_BAR:-commercial-grade}"
CONSTRAINTS="${CONSTRAINTS:-}"

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
RESEARCH_DIR="${ROOT_DIR}/artifacts/research/${INIT_ID}"
PRD_DIR="${ROOT_DIR}/artifacts/prd/${INIT_ID}"
DESIGN_DIR="${ROOT_DIR}/artifacts/design/${INIT_ID}"
PLANS_DIR="${ROOT_DIR}/artifacts/plans/${INIT_ID}"
RELEASE_DIR="${ROOT_DIR}/artifacts/releases/${INIT_ID}"
INDEX_DIR="${ROOT_DIR}/artifacts/initiatives"
INITIATIVE_DIR="${INDEX_DIR}/${INIT_ID}"
INDEX_FILE="${INDEX_DIR}/${INIT_ID}.md"
SPEC_FILE="${INITIATIVE_DIR}/initiative.yaml"
RUN_STATUS_FILE="${INITIATIVE_DIR}/run-status.md"
NEXT_COMMAND_FILE="${INITIATIVE_DIR}/next-command.md"

mkdir -p "${RESEARCH_DIR}" "${PRD_DIR}" "${DESIGN_DIR}" "${PLANS_DIR}" "${RELEASE_DIR}" "${INDEX_DIR}" "${INITIATIVE_DIR}"

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
    s/\{\{PLATFORM_YAML\}\}/$ENV{PLATFORM_YAML}/g;
    s/\{\{STACK_YAML\}\}/$ENV{STACK_YAML}/g;
    s/\{\{PRODUCT_CATEGORY_YAML\}\}/$ENV{PRODUCT_CATEGORY_YAML}/g;
    s/\{\{MARKETS_YAML\}\}/$ENV{MARKETS_YAML}/g;
    s/\{\{RESEARCH_WINDOW_YAML\}\}/$ENV{RESEARCH_WINDOW_YAML}/g;
    s/\{\{SEED_COMPETITORS_YAML\}\}/$ENV{SEED_COMPETITORS_YAML}/g;
    s/\{\{SOURCE_LOCALE_YAML\}\}/$ENV{SOURCE_LOCALE_YAML}/g;
    s/\{\{TARGET_LOCALES_YAML\}\}/$ENV{TARGET_LOCALES_YAML}/g;
    s/\{\{QUALITY_BAR_YAML\}\}/$ENV{QUALITY_BAR_YAML}/g;
    s/\{\{CONSTRAINTS_YAML\}\}/$ENV{CONSTRAINTS_YAML}/g;
  ' "${template_path}" > "${output_path}"
}

export INIT_ID DATE_STAMP SLUG TITLE
export GOAL_YAML="$(yaml_escape "${GOAL}")"
export REPOSITORY_YAML="$(yaml_escape "${REPOSITORY}")"
export PLATFORM_YAML="$(yaml_escape "${PLATFORM}")"
export STACK_YAML="$(yaml_escape "${STACK}")"
export PRODUCT_CATEGORY_YAML="$(yaml_escape "${PRODUCT_CATEGORY}")"
export MARKETS_YAML="$(yaml_escape "${MARKETS}")"
export RESEARCH_WINDOW_YAML="$(yaml_escape "${RESEARCH_WINDOW}")"
export SEED_COMPETITORS_YAML="$(yaml_escape "${SEED_COMPETITORS}")"
export SOURCE_LOCALE_YAML="$(yaml_escape "${SOURCE_LOCALE}")"
export TARGET_LOCALES_YAML="$(yaml_escape "${TARGET_LOCALES}")"
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
./scripts/supernb run --initiative-id ${INIT_ID}
\`\`\`
EOF

cat > "${NEXT_COMMAND_FILE}" <<EOF
# Next Command

Run \`./scripts/supernb run --initiative-id ${INIT_ID}\` to generate the next structured command brief for this initiative.
EOF

cat <<EOF
Initialized initiative scaffold: ${INIT_ID}

Created:
  ${INDEX_FILE}
  ${SPEC_FILE}
  ${RUN_STATUS_FILE}
  ${NEXT_COMMAND_FILE}
  ${RESEARCH_DIR}/01-competitor-landscape.md
  ${RESEARCH_DIR}/02-review-insights.md
  ${RESEARCH_DIR}/03-feature-opportunities.md
  ${PRD_DIR}/product-requirements.md
  ${DESIGN_DIR}/ui-ux-spec.md
  ${DESIGN_DIR}/i18n-strategy.md
  ${PLANS_DIR}/implementation-plan.md
  ${RELEASE_DIR}/release-readiness.md

Recommended next step:
  Run ./scripts/supernb run --initiative-id ${INIT_ID}
EOF
