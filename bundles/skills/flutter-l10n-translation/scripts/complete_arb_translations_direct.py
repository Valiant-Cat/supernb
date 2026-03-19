#!/usr/bin/env python3
"""
Complete missing/untranslated translations for ARB files using OpenAI API.

Policy (by default):
- Use a base ARB (usually English) as the source of truth.
- For each target ARB, translate only entries that are missing / non-string / identical to base.
- Preserve ICU/placeholder variable names (e.g., {count}, {count, plural, ...}).
- Never modify metadata keys (those starting with "@").

Usage:
  export OPENAI_API_KEY="sk-..."
  python3 complete_arb_translations_direct.py --l10n-dir path/to/lib/l10n
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import openai

from _path_guess import guess_l10n_dir, split_csv, uniq


ICU_VAR_RE = re.compile(r"\{([a-zA-Z_]\w*)\b")


def _icu_vars(s: str) -> set[str]:
    return set(ICU_VAR_RE.findall(s or ""))


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _pick_base_arb(l10n_dir: Path, base_arb: str | None) -> Path:
    if base_arb:
        p = l10n_dir / base_arb
        if not p.exists():
            raise SystemExit(f"Base ARB not found: {p}")
        return p

    if (l10n_dir / "app_en.arb").exists():
        return l10n_dir / "app_en.arb"

    en = sorted(l10n_dir.glob("*_en.arb"))
    if en:
        return en[0]

    raise SystemExit(
        'Unable to find base ARB; pass "--base-arb" (e.g., app_en.arb / intl_en.arb).'
    )


def _iter_targets(l10n_dir: Path, base_path: Path) -> Iterable[Path]:
    for p in sorted(l10n_dir.glob("*.arb")):
        if p == base_path:
            continue
        yield p


def _locale_from_filename(path: Path) -> str:
    stem = path.stem
    if "_" in stem:
        return stem.rsplit("_", 1)[1]
    return stem


def _language_name(locale: str) -> str:
    # Keep small and dependency-free; fallback to locale string.
    mapping = {
        "ar": "Arabic",
        "bn": "Bengali",
        "de": "German",
        "en": "English",
        "es": "Spanish",
        "fa": "Persian",
        "fr": "French",
        "hi": "Hindi",
        "id": "Indonesian",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "mr": "Marathi",
        "pt": "Portuguese",
        "ru": "Russian",
        "sw": "Swahili",
        "ta": "Tamil",
        "te": "Telugu",
        "tr": "Turkish",
        "ur": "Urdu",
        "vi": "Vietnamese",
        "zh": "Chinese",
        "zh-Hans": "Chinese (Simplified)",
        "zh-Hant": "Chinese (Traditional)",
    }
    return mapping.get(locale, locale)


def _needs_translation(
    base_value: Any,
    target_value: Any,
    key: str,
    *,
    treat_same_as_base: bool,
    allow_unchanged_keys: set[str],
    allow_unchanged_values: set[str],
) -> bool:
    if not isinstance(target_value, str):
        return True
    if not isinstance(base_value, str):
        return False
    if key in allow_unchanged_keys:
        return False
    if target_value in allow_unchanged_values:
        return False
    if treat_same_as_base and target_value == base_value:
        return True
    return False


def _parse_kv_lines(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def _translate_batch(
    client: openai.OpenAI,
    model: str,
    items: List[dict[str, str]],
    *,
    source_language: str,
    target_language: str,
    do_not_translate_terms: list[str],
) -> Dict[str, str]:
    if not items:
        return {}

    batch_text = "\n".join(f"{item['key']}: {item['value']}" for item in items)
    brand_line = ""
    if do_not_translate_terms:
        brand_line = "\n5. Do NOT translate these terms: " + ", ".join(f'"{t}"' for t in do_not_translate_terms)

    system_prompt = f"""You are a professional translator specializing in mobile app localization.
Translate the following UI strings from {source_language} to {target_language}.

CRITICAL RULES:
1. Preserve ICU MessageFormat syntax and variable names exactly (e.g., {{count}}, {{count, plural, one{{...}} other{{...}}}})
2. Preserve ALL variables: anything like {{name}} or {{name, ...}} must keep the same variable name(s)
3. Return translations in format: KEY: translated value
4. Use natural, user-friendly {target_language} appropriate for mobile apps{brand_line}
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": batch_text},
        ],
        temperature=0.3,
        max_tokens=4000,
    )
    return _parse_kv_lines(resp.choices[0].message.content or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete missing/untranslated ARB strings via OpenAI")
    parser.add_argument("--l10n-dir", default=None, help="Directory containing *.arb files")
    parser.add_argument("--base-arb", default=None, help="Base ARB filename (default: app_en.arb)")
    parser.add_argument(
        "--treat-same-as-base",
        default="true",
        choices=["true", "false"],
        help="If true, values identical to base are treated as untranslated (default: true)",
    )
    parser.add_argument(
        "--allow-unchanged-keys",
        default="",
        help="Comma-separated keys that are allowed to remain identical to base",
    )
    parser.add_argument(
        "--allow-unchanged-values",
        default="",
        help="Comma-separated values (proper nouns/acronyms) allowed to remain unchanged",
    )
    parser.add_argument(
        "--do-not-translate-terms",
        default="",
        help="Comma-separated terms that must not be translated (brand/product names)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help='OpenAI API key (defaults to env var "OPENAI_API_KEY")',
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model")
    parser.add_argument("--batch-size", type=int, default=30, help="Strings per API request")
    parser.add_argument("--sleep", type=float, default=1.0, help="Sleep seconds between batches")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print('❌ Missing API key. Set env var "OPENAI_API_KEY" or pass --api-key.')
        return 2

    l10n_dir = Path(args.l10n_dir) if args.l10n_dir else (guess_l10n_dir(Path.cwd()) or None)
    if not l10n_dir:
        raise SystemExit('Unable to auto-detect l10n dir; pass "--l10n-dir".')
    if not l10n_dir.exists():
        raise SystemExit(f"l10n dir not found: {l10n_dir}")

    base_path = _pick_base_arb(l10n_dir, args.base_arb)
    base = _load(base_path)
    base_keys = [k for k in base.keys() if not k.startswith("@") and isinstance(base.get(k), str)]

    treat_same_as_base = args.treat_same_as_base.lower() == "true"
    allow_unchanged_keys = set(uniq(split_csv(args.allow_unchanged_keys)))
    allow_unchanged_values = set(uniq(split_csv(args.allow_unchanged_values)))
    do_not_translate_terms = uniq(split_csv(args.do_not_translate_terms))

    client = openai.OpenAI(api_key=api_key)

    total_translated = 0
    targets_processed = 0

    for target_path in _iter_targets(l10n_dir, base_path):
        locale = _locale_from_filename(target_path)
        target_language = _language_name(locale)

        target = _load(target_path)
        items: List[dict[str, str]] = []
        for key in base_keys:
            if _needs_translation(
                base.get(key),
                target.get(key),
                key,
                treat_same_as_base=treat_same_as_base,
                allow_unchanged_keys=allow_unchanged_keys,
                allow_unchanged_values=allow_unchanged_values,
            ):
                items.append({"key": key, "value": str(base[key])})

        if not items:
            continue

        print(f"📂 {target_path.name} ({target_language}): {len(items)} strings to translate")
        targets_processed += 1

        for i in range(0, len(items), max(1, args.batch_size)):
            batch = items[i : i + max(1, args.batch_size)]
            try:
                results = _translate_batch(
                    client,
                    args.model,
                    batch,
                    source_language="English",
                    target_language=target_language,
                    do_not_translate_terms=do_not_translate_terms,
                )
            except Exception as e:
                print(f"   ❌ Translation API error: {e}")
                continue

            for item in batch:
                key = item["key"]
                if key not in results:
                    continue
                candidate = results[key]

                # Validate ICU variable preservation against base.
                if _icu_vars(item["value"]) != _icu_vars(candidate):
                    continue

                if treat_same_as_base and candidate == item["value"] and key not in allow_unchanged_keys:
                    continue

                target[key] = candidate
                total_translated += 1

            if i + args.batch_size < len(items) and args.sleep > 0:
                time.sleep(args.sleep)

        _save(target_path, target)
        print(f"   ✅ wrote: {target_path}")

    print(f"\n✅ Done. Targets processed: {targets_processed}, strings translated: {total_translated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

