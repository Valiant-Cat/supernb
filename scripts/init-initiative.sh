#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="${ROOT_DIR}/templates"
DATE_STAMP="$(date +%F)"

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
INDEX_FILE="${INDEX_DIR}/${INIT_ID}.md"

mkdir -p "${RESEARCH_DIR}" "${PRD_DIR}" "${DESIGN_DIR}" "${PLANS_DIR}" "${RELEASE_DIR}" "${INDEX_DIR}"

render_template() {
  local template_path="$1"
  local output_path="$2"

  perl -0pe '
    s/\{\{INIT_ID\}\}/$ENV{INIT_ID}/g;
    s/\{\{DATE_STAMP\}\}/$ENV{DATE_STAMP}/g;
    s/\{\{SLUG\}\}/$ENV{SLUG}/g;
    s/\{\{TITLE\}\}/$ENV{TITLE}/g;
  ' "${template_path}" > "${output_path}"
}

export INIT_ID DATE_STAMP SLUG TITLE

render_template "${TEMPLATES_DIR}/initiative-index.md" "${INDEX_FILE}"
render_template "${TEMPLATES_DIR}/research/01-competitor-landscape.md" "${RESEARCH_DIR}/01-competitor-landscape.md"
render_template "${TEMPLATES_DIR}/research/02-review-insights.md" "${RESEARCH_DIR}/02-review-insights.md"
render_template "${TEMPLATES_DIR}/research/03-feature-opportunities.md" "${RESEARCH_DIR}/03-feature-opportunities.md"
render_template "${TEMPLATES_DIR}/prd/product-requirements.md" "${PRD_DIR}/product-requirements.md"
render_template "${TEMPLATES_DIR}/design/ui-ux-spec.md" "${DESIGN_DIR}/ui-ux-spec.md"
render_template "${TEMPLATES_DIR}/design/i18n-strategy.md" "${DESIGN_DIR}/i18n-strategy.md"
render_template "${TEMPLATES_DIR}/plans/implementation-plan.md" "${PLANS_DIR}/implementation-plan.md"
render_template "${TEMPLATES_DIR}/releases/release-readiness.md" "${RELEASE_DIR}/release-readiness.md"

cat <<EOF
Initialized initiative scaffold: ${INIT_ID}

Created:
  ${INDEX_FILE}
  ${RESEARCH_DIR}/01-competitor-landscape.md
  ${RESEARCH_DIR}/02-review-insights.md
  ${RESEARCH_DIR}/03-feature-opportunities.md
  ${PRD_DIR}/product-requirements.md
  ${DESIGN_DIR}/ui-ux-spec.md
  ${DESIGN_DIR}/i18n-strategy.md
  ${PLANS_DIR}/implementation-plan.md
  ${RELEASE_DIR}/release-readiness.md

Recommended next step:
  Use the product-research-prd skill and fill the research files first.
EOF
