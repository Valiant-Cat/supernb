#!/usr/bin/env bash

ensure_symlink_if_missing() {
  local source_path="$1"
  local target_path="$2"
  local label="$3"

  mkdir -p "$(dirname "${target_path}")"

  if [[ -L "${target_path}" ]]; then
    local current_target
    current_target="$(readlink "${target_path}")"

    if [[ "${current_target}" == "${source_path}" ]]; then
      echo "  already installed: ${label}"
    else
      echo "  skipped existing link: ${label} (${target_path} -> ${current_target})"
    fi
    return 0
  fi

  if [[ -e "${target_path}" ]]; then
    echo "  skipped existing path: ${label} (${target_path})"
    return 0
  fi

  ln -s "${source_path}" "${target_path}"
  echo "  installed: ${label}"
}

ensure_symlink_with_repair() {
  local source_path="$1"
  local target_path="$2"
  local label="$3"
  local repair_mode="${4:-skip}"

  mkdir -p "$(dirname "${target_path}")"

  if [[ -L "${target_path}" ]]; then
    local current_target
    current_target="$(readlink "${target_path}")"

    if [[ "${current_target}" == "${source_path}" ]]; then
      echo "  already installed: ${label}"
    else
      echo "  skipped existing link: ${label} (${target_path} -> ${current_target})"
    fi
    return 0
  fi

  if [[ -e "${target_path}" ]]; then
    if [[ "${repair_mode}" == "replace_skill_dir" && -d "${target_path}" && -f "${target_path}/SKILL.md" ]]; then
      rm -rf "${target_path}"
      ln -s "${source_path}" "${target_path}"
      echo "  repaired managed skill dir: ${label}"
      return 0
    fi

    echo "  skipped existing path: ${label} (${target_path})"
    return 0
  fi

  ln -s "${source_path}" "${target_path}"
  echo "  installed: ${label}"
}

sync_directory_as_symlinks() {
  local source_dir="$1"
  local target_dir="$2"
  local label_prefix="$3"
  local repair_mode="${4:-skip}"

  mkdir -p "${target_dir}"

  local item
  shopt -s dotglob nullglob
  for item in "${source_dir}"/*; do
    local base_name
    base_name="$(basename "${item}")"
    ensure_symlink_with_repair "${item}" "${target_dir}/${base_name}" "${label_prefix}/${base_name}" "${repair_mode}"
  done
  shopt -u dotglob nullglob
}

copy_tree_contents_if_missing() {
  local source_dir="$1"
  local target_dir="$2"
  local label_prefix="$3"

  mkdir -p "${target_dir}"

  local item
  shopt -s dotglob nullglob
  for item in "${source_dir}"/*; do
    local base_name
    local target_path

    base_name="$(basename "${item}")"
    target_path="${target_dir}/${base_name}"

    if [[ -e "${target_path}" || -L "${target_path}" ]]; then
      echo "  skipped existing path: ${label_prefix}/${base_name}"
      continue
    fi

    cp -R "${item}" "${target_path}"
    echo "  installed: ${label_prefix}/${base_name}"
  done
  shopt -u dotglob nullglob
}
