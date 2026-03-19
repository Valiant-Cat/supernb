#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMMAND=""
TITLE=""
INITIATIVE_ID=""
BRIEF_DIR="${ROOT_DIR}/artifacts/commands"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

declare -a FORWARD_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  ./scripts/save-command-brief.sh --command <command-name> [options forwarded to render-command]

Options:
  --title <text>            Optional human-readable title
  --initiative-id <id>      Optional initiative id
  --brief-dir <path>        Optional output directory
  All render-command options are supported and forwarded.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --command)
      COMMAND="${2:-}"
      FORWARD_ARGS+=("$1" "$2")
      shift 2
      ;;
    --title)
      TITLE="${2:-}"
      shift 2
      ;;
    --initiative-id)
      INITIATIVE_ID="${2:-}"
      shift 2
      ;;
    --brief-dir)
      BRIEF_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      FORWARD_ARGS+=("$1")
      if [[ $# -gt 1 && ! "$2" =~ ^-- ]]; then
        FORWARD_ARGS+=("$2")
        shift 2
      else
        shift
      fi
      ;;
  esac
done

if [[ -z "${COMMAND}" ]]; then
  echo "--command is required." >&2
  usage >&2
  exit 1
fi

mkdir -p "${BRIEF_DIR}"

SLUG="$(printf '%s' "${COMMAND}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
OUTPUT_FILE="${BRIEF_DIR}/${TIMESTAMP}-${SLUG}.md"

{
  echo "# Command Brief"
  echo
  echo "- Command: \`${COMMAND}\`"
  echo "- Created: \`$(date +%F)\`"
  if [[ -n "${TITLE}" ]]; then echo "- Title: \`${TITLE}\`"; fi
  if [[ -n "${INITIATIVE_ID}" ]]; then echo "- Initiative ID: \`${INITIATIVE_ID}\`"; fi
  echo
  echo "## Prompt"
  echo
  echo '```text'
  "${ROOT_DIR}/scripts/render-command.sh" "${FORWARD_ARGS[@]}"
  echo '```'
} > "${OUTPUT_FILE}"

echo "Saved command brief: ${OUTPUT_FILE}"

