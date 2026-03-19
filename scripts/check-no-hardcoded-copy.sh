#!/usr/bin/env bash

set -euo pipefail

TARGET_DIR="${1:-.}"
cd "${TARGET_DIR}"

if ! command -v rg >/dev/null 2>&1; then
  echo "rg is required for check-no-hardcoded-copy.sh" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

RESULTS_FILE="${TMP_DIR}/hardcoded-copy.txt"
FILES_FILE="${TMP_DIR}/candidate-files.txt"

COMMON_GLOBS=(
  --glob '!**/.git/**'
  --glob '!**/node_modules/**'
  --glob '!**/.next/**'
  --glob '!**/dist/**'
  --glob '!**/build/**'
  --glob '!**/coverage/**'
  --glob '!**/vendor/**'
  --glob '!**/Pods/**'
  --glob '!**/.dart_tool/**'
  --glob '!**/.gradle/**'
  --glob '!**/generated/**'
  --glob '!**/gen/**'
  --glob '!**/__snapshots__/**'
  --glob '!**/__tests__/**'
  --glob '!**/test/**'
  --glob '!**/tests/**'
  --glob '!**/spec/**'
  --glob '!**/specs/**'
  --glob '!**/fixtures/**'
  --glob '!**/storybook-static/**'
  --glob '!**/stories/**'
  --glob '!**/*.md'
  --glob '!**/*.arb'
  --glob '!**/*.properties'
  --glob '!**/*.po'
  --glob '!**/*.pot'
  --glob '!**/*.json'
  --glob '!**/*.yaml'
  --glob '!**/*.yml'
  --glob '!**/*.xml'
  --glob '!**/*.svg'
  --glob '!**/*.html'
  --glob '!**/l10n/**'
  --glob '!**/locales/**'
  --glob '!**/i18n/**'
)

# Build candidate source file list first so the actual scans are deterministic.
rg --files \
  "${COMMON_GLOBS[@]}" \
  --glob '*.js' \
  --glob '*.jsx' \
  --glob '*.ts' \
  --glob '*.tsx' \
  --glob '*.vue' \
  --glob '*.svelte' \
  --glob '*.dart' \
  --glob '*.kt' \
  --glob '*.kts' \
  --glob '*.java' \
  --glob '*.swift' \
  --glob '*.m' \
  --glob '*.mm' \
  --glob '*.py' \
  > "${FILES_FILE}" || true

if [[ ! -s "${FILES_FILE}" ]]; then
  echo "No candidate source files found for hardcoded-copy scan."
  exit 0
fi

# Heuristic 1: suspicious user-facing string literals in code.
rg --pcre2 --with-filename --line-number --no-heading --color never \
  '(?i)(["'"'"'`])([[:alpha:]][^"'"'"'`]{2,}(?:[[:space:][:punct:]][^"'"'"'`]{1,})?)\1' \
  $(cat "${FILES_FILE}") \
  | rg -v 'supernb-ignore-hardcoded-copy|https?://|^[^:]+:[0-9]+:.*(import |export |class |interface |enum |type |case |switch |console\.|logger\.|throw new |Error\(|Exception\(|assert\(|test\(|describe\(|it\(|expect\()|^[^:]+:[0-9]+:.*\b(t|tr|translate|getString|stringResource)\s*\(\s*["'"'"'`][A-Za-z0-9_.-]+["'"'"'`]' \
  > "${RESULTS_FILE}" || true

# Heuristic 2: common UI props with raw text values in component or layout code.
rg --pcre2 --with-filename --line-number --no-heading --color never \
  '(?i)\b(title|label|placeholder|helperText|hint|tooltip|emptyText|errorText|successText|contentDescription|aria-label|ariaLabel|text)\s*[:=]\s*(["'"'"']).{1,}\2' \
  $(cat "${FILES_FILE}") \
  | rg -v 'supernb-ignore-hardcoded-copy' \
  >> "${RESULTS_FILE}" || true

sort -u "${RESULTS_FILE}" -o "${RESULTS_FILE}"

if [[ -s "${RESULTS_FILE}" ]]; then
  echo "Potential hardcoded user-facing copy found." >&2
  echo "" >&2
  echo "Review these lines and externalize real UI copy into localization resources." >&2
  echo "Use an explicit 'supernb-ignore-hardcoded-copy' marker only for intentional non-user-facing literals." >&2
  echo "" >&2
  cat "${RESULTS_FILE}" >&2
  exit 1
fi

echo "No obvious hardcoded user-facing copy detected."
