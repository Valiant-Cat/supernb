#!/usr/bin/env bash

set -euo pipefail

STACK=""
TARGET_DIR="."
SOURCE_LOCALE="en"
TARGET_LOCALES=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/init-i18n-foundation.sh --stack <flutter|android|web|ios|generic> [options]

Options:
  --target-dir <path>       Project root to initialize. Default: .
  --source-locale <locale>  Source locale. Default: en
  --target-locales <list>   Comma-separated locales, e.g. zh-CN,ja,th
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack)
      STACK="${2:-}"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="${2:-}"
      shift 2
      ;;
    --source-locale)
      SOURCE_LOCALE="${2:-}"
      shift 2
      ;;
    --target-locales)
      TARGET_LOCALES="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${STACK}" ]]; then
  echo "--stack is required." >&2
  usage >&2
  exit 1
fi

TARGET_DIR="$(cd "${TARGET_DIR}" && pwd)"
IFS=',' read -r -a LOCALES <<< "${TARGET_LOCALES}"

write_file_if_missing() {
  local path="$1"
  local content="$2"
  mkdir -p "$(dirname "${path}")"
  if [[ ! -f "${path}" ]]; then
    printf '%s' "${content}" > "${path}"
  fi
}

normalize_android_locale_dir() {
  local locale="$1"
  local normalized="${locale//-/-r}"
  printf '%s' "${normalized}"
}

init_flutter() {
  local l10n_dir="${TARGET_DIR}/lib/l10n"
  mkdir -p "${l10n_dir}"
  write_file_if_missing "${TARGET_DIR}/l10n.yaml" "arb-dir: lib/l10n
template-arb-file: app_${SOURCE_LOCALE}.arb
output-localization-file: app_localizations.dart
"
  write_file_if_missing "${l10n_dir}/app_${SOURCE_LOCALE}.arb" "{
  \"@@locale\": \"${SOURCE_LOCALE}\",
  \"appTitle\": \"\",
  \"@appTitle\": {
    \"description\": \"Application title\"
  }
}
"
  for locale in "${LOCALES[@]}"; do
    [[ -n "${locale}" ]] || continue
    write_file_if_missing "${l10n_dir}/app_${locale}.arb" "{
  \"@@locale\": \"${locale}\",
  \"appTitle\": \"\"
}
"
  done
}

init_android() {
  local res_dir="${TARGET_DIR}/app/src/main/res"
  mkdir -p "${res_dir}/values"
  write_file_if_missing "${res_dir}/values/strings.xml" "<resources>
    <string name=\"app_name\"></string>
</resources>
"
  for locale in "${LOCALES[@]}"; do
    [[ -n "${locale}" ]] || continue
    local dir_locale
    dir_locale="$(normalize_android_locale_dir "${locale}")"
    mkdir -p "${res_dir}/values-${dir_locale}"
    write_file_if_missing "${res_dir}/values-${dir_locale}/strings.xml" "<resources>
    <string name=\"app_name\"></string>
</resources>
"
  done
}

init_web() {
  local locale_root="${TARGET_DIR}/locales"
  mkdir -p "${locale_root}/${SOURCE_LOCALE}"
  write_file_if_missing "${locale_root}/${SOURCE_LOCALE}/common.json" "{
  \"app.title\": \"\"
}
"
  for locale in "${LOCALES[@]}"; do
    [[ -n "${locale}" ]] || continue
    mkdir -p "${locale_root}/${locale}"
    write_file_if_missing "${locale_root}/${locale}/common.json" "{
  \"app.title\": \"\"
}
"
  done
}

init_ios() {
  local runner_dir
  if [[ -d "${TARGET_DIR}/ios/Runner" ]]; then
    runner_dir="${TARGET_DIR}/ios/Runner"
  else
    runner_dir="${TARGET_DIR}/Runner"
  fi
  mkdir -p "${runner_dir}"
  write_file_if_missing "${runner_dir}/${SOURCE_LOCALE}.lproj/Localizable.strings" "\"app_title\" = \"\";
"
  for locale in "${LOCALES[@]}"; do
    [[ -n "${locale}" ]] || continue
    write_file_if_missing "${runner_dir}/${locale}.lproj/Localizable.strings" "\"app_title\" = \"\";
"
  done
}

init_generic() {
  local locale_root="${TARGET_DIR}/locales"
  mkdir -p "${locale_root}"
  write_file_if_missing "${locale_root}/${SOURCE_LOCALE}.json" "{
  \"app.title\": \"\"
}
"
  for locale in "${LOCALES[@]}"; do
    [[ -n "${locale}" ]] || continue
    write_file_if_missing "${locale_root}/${locale}.json" "{
  \"app.title\": \"\"
}
"
  done
}

case "${STACK}" in
  flutter) init_flutter ;;
  android) init_android ;;
  web) init_web ;;
  ios) init_ios ;;
  generic) init_generic ;;
  *)
    echo "Unsupported stack: ${STACK}" >&2
    exit 1
    ;;
esac

cat <<EOF
Initialized i18n foundation
  stack: ${STACK}
  target_dir: ${TARGET_DIR}
  source_locale: ${SOURCE_LOCALE}
  target_locales: ${TARGET_LOCALES:-none}
EOF
