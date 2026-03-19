#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMAND=""
GOAL=""
REPOSITORY=""
PLATFORM=""
STACK=""
MARKETS=""
LOCALES=""
CONSTRAINTS=""
SOURCE_LOCALE=""
TARGET_LOCALES=""
CAPABILITY_HINT=""
TRANSLATION_CONSTRAINTS=""
PRODUCT_CATEGORY=""
SEED_COMPETITORS=""
RESEARCH_WINDOW=""
QUALITY_BAR=""
INITIATIVE_ID=""
OUTPUT_FILE=""
STRICT=0

declare -a CONTEXT_LINES=()
declare -a OUTPUT_LINES=()

usage() {
  cat <<'EOF'
Usage:
  ./scripts/render-command.sh --command <command-name> [options]

Options:
  --goal <text>
  --repository <path-or-url>
  --platform <platform>
  --stack <stack>
  --markets <markets>
  --locales <locales>
  --constraints <text>
  --source-locale <locale>
  --target-locales <locales>
  --capability-hint <hint>
  --translation-constraints <text>
  --product-category <text>
  --seed-competitors <text>
  --research-window <text>
  --quality-bar <text>
  --initiative-id <id>
  --context-line <text>      Repeatable
  --output-line <text>       Repeatable
  --output-file <path>
  --strict
EOF
}

default_output_lines() {
  case "${COMMAND}" in
    supernb-orchestrator)
      printf '%s\n' \
        "route to the correct supernb workflow" \
        "preserve required phase gates" \
        "save artifacts locally when needed"
      ;;
    full-product-delivery)
      printf '%s\n' \
        "create initiative artifacts" \
        "produce research, PRD, design, plan, implementation, and release evidence" \
        "commit validated changes"
      ;;
    product-research-prd)
      printf '%s\n' \
        "collect the smallest useful evidence set" \
        "produce research notes and a cited PRD" \
        "separate evidence-backed conclusions from open hypotheses"
      ;;
    single-capability-router)
      printf '%s\n' \
        "route to the narrowest matching upstream capability" \
        "save artifacts locally if needed"
      ;;
    brainstorm-and-save)
      printf '%s\n' \
        "save the brainstormed result into local markdown artifacts"
      ;;
    ui-ux-governance)
      printf '%s\n' \
        "define or critique the design system and page-level UX" \
        "check contrast, readability, and state coverage" \
        "save design audit notes locally"
      ;;
    ui-ux-upgrade)
      printf '%s\n' \
        "define the upgrade direction" \
        "implement the changes" \
        "run a final design audit"
      ;;
    autonomous-delivery)
      printf '%s\n' \
        "refine the implementation plan" \
        "execute in validated batches with tests first" \
        "commit each verified batch"
      ;;
    implementation-execution)
      printf '%s\n' \
        "plan the work" \
        "implement and verify it" \
        "commit validated changes"
      ;;
    i18n-localization-governance)
      printf '%s\n' \
        "externalize user-facing copy" \
        "initialize or update localization resources" \
        "sync target locales" \
        "run hardcoded-copy checks"
      ;;
  esac
}

command_file() {
  printf '%s/commands/%s.md\n' "${ROOT_DIR}" "${COMMAND}"
}

known_command() {
  [[ -f "$(command_file)" ]]
}

emit_context_line() {
  local label="$1"
  local value="$2"
  local placeholder="$3"
  echo "- ${label}: ${value:-${placeholder}}"
}

has_missing_required_fields() {
  local missing=1

  case "${COMMAND}" in
    full-product-delivery|product-research-prd)
      [[ -n "${PRODUCT_CATEGORY}" || -n "${SEED_COMPETITORS}" ]] || missing=0
      [[ -n "${MARKETS}" ]] || missing=0
      [[ -n "${RESEARCH_WINDOW}" ]] || missing=0
      ;;
    single-capability-router)
      [[ -n "${CAPABILITY_HINT}" ]] || missing=0
      ;;
    autonomous-delivery|implementation-execution|ui-ux-governance|ui-ux-upgrade)
      [[ -n "${REPOSITORY}" ]] || missing=0
      ;;
  esac

  return "${missing}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --command) COMMAND="${2:-}"; shift 2 ;;
    --goal) GOAL="${2:-}"; shift 2 ;;
    --repository) REPOSITORY="${2:-}"; shift 2 ;;
    --platform) PLATFORM="${2:-}"; shift 2 ;;
    --stack) STACK="${2:-}"; shift 2 ;;
    --markets) MARKETS="${2:-}"; shift 2 ;;
    --locales) LOCALES="${2:-}"; shift 2 ;;
    --constraints) CONSTRAINTS="${2:-}"; shift 2 ;;
    --source-locale) SOURCE_LOCALE="${2:-}"; shift 2 ;;
    --target-locales) TARGET_LOCALES="${2:-}"; shift 2 ;;
    --capability-hint) CAPABILITY_HINT="${2:-}"; shift 2 ;;
    --translation-constraints) TRANSLATION_CONSTRAINTS="${2:-}"; shift 2 ;;
    --product-category) PRODUCT_CATEGORY="${2:-}"; shift 2 ;;
    --seed-competitors) SEED_COMPETITORS="${2:-}"; shift 2 ;;
    --research-window) RESEARCH_WINDOW="${2:-}"; shift 2 ;;
    --quality-bar) QUALITY_BAR="${2:-}"; shift 2 ;;
    --initiative-id) INITIATIVE_ID="${2:-}"; shift 2 ;;
    --context-line) CONTEXT_LINES+=("${2:-}"); shift 2 ;;
    --output-line) OUTPUT_LINES+=("${2:-}"); shift 2 ;;
    --output-file) OUTPUT_FILE="${2:-}"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${COMMAND}" ]]; then
  echo "--command is required." >&2
  usage >&2
  exit 1
fi

if ! known_command; then
  echo "Unknown command: ${COMMAND}" >&2
  echo "" >&2
  echo "Available commands:" >&2
  find "${ROOT_DIR}/commands" -maxdepth 1 -type f -name '*.md' ! -name 'README.md' -exec basename {} .md \; | sort >&2
  exit 1
fi

if [[ "${STRICT}" -eq 1 ]] && has_missing_required_fields; then
  echo "Missing required fields for command: ${COMMAND}" >&2
  exit 1
fi

render() {
  echo "Use supernb command: ${COMMAND}"
  echo "Goal: ${GOAL:-<fill goal>}"
  echo "Context:"

  case "${COMMAND}" in
    full-product-delivery)
      emit_context_line "repository" "${REPOSITORY}" "<fill repository url or local path>"
      emit_context_line "platform" "${PLATFORM}" "<fill target platform or product surface>"
      emit_context_line "stack" "${STACK}" "<fill frameworks or languages>"
      emit_context_line "product category" "${PRODUCT_CATEGORY}" "<fill product category>"
      emit_context_line "seed competitors" "${SEED_COMPETITORS}" "<fill seed competitors if known>"
      emit_context_line "markets" "${MARKETS}" "<fill target markets or countries>"
      emit_context_line "research window" "${RESEARCH_WINDOW}" "<fill research date window>"
      emit_context_line "locales" "${LOCALES}" "<fill required locales if relevant>"
      emit_context_line "quality bar" "${QUALITY_BAR}" "<fill commercial quality bar>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints>"
      ;;
    product-research-prd)
      emit_context_line "repository" "${REPOSITORY}" "<optional repository url or local path>"
      emit_context_line "product category" "${PRODUCT_CATEGORY}" "<fill product category>"
      emit_context_line "seed competitors" "${SEED_COMPETITORS}" "<fill seed competitors if known>"
      emit_context_line "markets" "${MARKETS}" "<fill target markets or countries>"
      emit_context_line "research window" "${RESEARCH_WINDOW}" "<fill research date window>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints>"
      ;;
    single-capability-router)
      emit_context_line "repository" "${REPOSITORY}" "<optional repository url or local path>"
      emit_context_line "stack" "${STACK}" "<fill framework or language if relevant>"
      emit_context_line "capability hint" "${CAPABILITY_HINT}" "<fill research|design|debugging|review|planning|translation|execution>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints if relevant>"
      ;;
    supernb-orchestrator)
      emit_context_line "repository" "${REPOSITORY}" "<optional repository url or local path>"
      emit_context_line "platform" "${PLATFORM}" "<fill target platform or product surface>"
      emit_context_line "stack" "${STACK}" "<fill frameworks or languages>"
      emit_context_line "initiative id" "${INITIATIVE_ID}" "<fill initiative id if it already exists>"
      emit_context_line "capability hint" "${CAPABILITY_HINT}" "<fill only if this is not a full-product request>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints>"
      ;;
    brainstorm-and-save)
      emit_context_line "repository" "${REPOSITORY}" "<optional repository url or local path>"
      emit_context_line "initiative id" "${INITIATIVE_ID}" "<fill initiative id if the brainstorm belongs to one>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints>"
      ;;
    ui-ux-governance|ui-ux-upgrade|autonomous-delivery|implementation-execution)
      emit_context_line "repository" "${REPOSITORY}" "<fill repository url or local path>"
      emit_context_line "platform" "${PLATFORM}" "<fill target platform if relevant>"
      emit_context_line "stack" "${STACK}" "<fill frameworks or languages>"
      emit_context_line "initiative id" "${INITIATIVE_ID}" "<fill initiative id if it already exists>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints>"
      ;;
    i18n-localization-governance)
      emit_context_line "repository" "${REPOSITORY}" "<fill repository url or local path>"
      emit_context_line "stack" "${STACK}" "<fill frameworks or languages>"
      emit_context_line "source locale" "${SOURCE_LOCALE}" "<fill source locale>"
      emit_context_line "target locales" "${TARGET_LOCALES}" "<fill target locales>"
      emit_context_line "translation constraints" "${TRANSLATION_CONSTRAINTS}" "<fill translation constraints>"
      emit_context_line "constraints" "${CONSTRAINTS}" "<fill constraints>"
      ;;
    *)
      if [[ -n "${REPOSITORY}" ]]; then echo "- repository: ${REPOSITORY}"; fi
      if [[ -n "${PLATFORM}" ]]; then echo "- platform: ${PLATFORM}"; fi
      if [[ -n "${STACK}" ]]; then echo "- stack: ${STACK}"; fi
      if [[ -n "${MARKETS}" ]]; then echo "- markets: ${MARKETS}"; fi
      if [[ -n "${LOCALES}" ]]; then echo "- locales: ${LOCALES}"; fi
      if [[ -n "${SOURCE_LOCALE}" ]]; then echo "- source locale: ${SOURCE_LOCALE}"; fi
      if [[ -n "${TARGET_LOCALES}" ]]; then echo "- target locales: ${TARGET_LOCALES}"; fi
      if [[ -n "${CAPABILITY_HINT}" ]]; then echo "- capability hint: ${CAPABILITY_HINT}"; fi
      if [[ -n "${CONSTRAINTS}" ]]; then echo "- constraints: ${CONSTRAINTS}"; fi
      if [[ -n "${TRANSLATION_CONSTRAINTS}" ]]; then echo "- translation constraints: ${TRANSLATION_CONSTRAINTS}"; fi
      ;;
  esac

  if [[ ${#CONTEXT_LINES[@]} -gt 0 ]]; then
    for line in "${CONTEXT_LINES[@]}"; do
      [[ -n "${line}" ]] && echo "- ${line}"
    done
  fi

  echo "Output:"
  if [[ ${#OUTPUT_LINES[@]} -gt 0 ]]; then
    for line in "${OUTPUT_LINES[@]}"; do
      [[ -n "${line}" ]] && echo "- ${line}"
    done
  else
    while IFS= read -r line; do
      [[ -n "${line}" ]] && echo "- ${line}"
    done < <(default_output_lines)
  fi
}

if [[ -n "${OUTPUT_FILE}" ]]; then
  render > "${OUTPUT_FILE}"
else
  render
fi
