---
name: android-i18n-translation
description: Android strings.xml localization and translation workflow for multi-locale projects. Use when extracting hardcoded text from layout XML, syncing missing keys across values-* locales, and auto-translating untranslated strings while preserving placeholders (%1$s, %s, {name}, \n).
---

# Android I18n Translation

Run this workflow from an Android project root.

Resolve the installed skill directory once before running the helper scripts:

```bash
resolve_skill_dir() {
  local skill_name="$1"
  local dir="$PWD"
  while [[ "$dir" != "/" ]]; do
    for base in "$dir/.claude/skills" "$dir/.opencode/skills"; do
      if [[ -f "$base/$skill_name/SKILL.md" ]]; then
        printf '%s\n' "$base/$skill_name"
        return 0
      fi
    done
    dir="$(dirname "$dir")"
  done
  for base in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.codex/skills"; do
    if [[ -f "$base/$skill_name/SKILL.md" ]]; then
      printf '%s\n' "$base/$skill_name"
      return 0
    fi
  done
  return 1
}

ANDROID_I18N_SKILL_DIR="$(resolve_skill_dir android-i18n-translation)"
```

## 1) Install dependencies

```bash
python3 -m pip install -r "$ANDROID_I18N_SKILL_DIR/scripts/requirements_translation.txt"
```

## 2) Extract hardcoded layout text to strings

```bash
python3 "$ANDROID_I18N_SKILL_DIR/scripts/localize_hardcoded_layout_texts.py" \
  --res-dir app/src/main/res
```

What it does:
- Scan `layout/*.xml` for `android:text|hint|contentDescription|title|summary` literals.
- Replace literals with `@string/layout_auto_*`.
- Write generated keys to `values/strings_layout_auto.xml`.

## 3) Sync and translate all locales

Use OpenAI (preferred):

```bash
export OPENAI_API_KEY="<your_key>"
python3 "$ANDROID_I18N_SKILL_DIR/scripts/complete_android_multifile_translations.py" \
  --res-dir app/src/main/res \
  --provider openai \
  --model gpt-4o-mini
```

Use Google fallback:

```bash
python3 "$ANDROID_I18N_SKILL_DIR/scripts/complete_android_multifile_translations.py" \
  --res-dir app/src/main/res \
  --provider google
```

What it does:
- Read base `values/strings*.xml`.
- Ensure each `values-*` locale has all keys.
- Copy from same-language peer locales when possible.
- Translate missing/untranslated entries in batches.
- Preserve placeholders and skip unsafe replacements.

## 4) Validate before shipping

```bash
./gradlew :app:mergeDebugResources
./gradlew :app:lintDebug
```

If formatting-related lint appears, avoid `getString(id, arg)` on keys where some locales are non-format templates; use safe placeholder replacement in code.

## Scripts

- `scripts/localize_hardcoded_layout_texts.py`
- `scripts/complete_android_multifile_translations.py`
- `scripts/requirements_translation.txt`
