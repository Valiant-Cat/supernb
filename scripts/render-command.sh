#!/usr/bin/env bash

set -euo pipefail

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
OUTPUT_FILE=""

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
  --context-line <text>      Repeatable
  --output-line <text>       Repeatable
  --output-file <path>
EOF
}

default_output_lines() {
  case "${COMMAND}" in
    full-product-delivery)
      printf '%s\n' \
        "create initiative artifacts" \
        "produce research, PRD, design, plan, implementation, and release evidence" \
        "commit validated changes"
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
    ui-ux-upgrade)
      printf '%s\n' \
        "define the upgrade direction" \
        "implement the changes" \
        "run a final design audit"
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
    --context-line) CONTEXT_LINES+=("${2:-}"); shift 2 ;;
    --output-line) OUTPUT_LINES+=("${2:-}"); shift 2 ;;
    --output-file) OUTPUT_FILE="${2:-}"; shift 2 ;;
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

render() {
  echo "Use supernb command: ${COMMAND}"
  echo "Goal: ${GOAL:-<fill goal>}"
  echo "Context:"

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
