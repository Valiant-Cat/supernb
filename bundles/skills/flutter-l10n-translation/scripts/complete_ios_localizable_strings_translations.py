#!/usr/bin/env python3
"""
Translate iOS Localizable.strings files using OpenAI.

Policy:
- Use `en.lproj/Localizable.strings` as English reference.
- For each locale, translate values identical to English.
- Preserve placeholders like %@ / %d / {count}.

Usage:
  export OPENAI_API_KEY="sk-..."
  python3 complete_ios_localizable_strings_translations.py --runner-dir path/to/ios/Runner
"""

from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import openai

from _path_guess import guess_ios_runner_dir, split_csv, uniq


LINE_RE = re.compile(r'^\s*"(?P<key>[^"]+)"\s*=\s*"(?P<val>(?:\\.|[^"])*)"\s*;\s*$')
PLACEHOLDER_CURLY = re.compile(r"\{(\w+)\}")
PLACEHOLDER_PRINTF = re.compile(r"%(?:\d+\\$)?[@sdfox]")  # %@, %d, %s, etc.


def _ios_unescape(s: str) -> str:
    return s.replace(r"\\", "\\").replace(r"\"", '"')


def _ios_escape(s: str) -> str:
    return s.replace("\\", r"\\").replace('"', r"\"")


def _placeholders(s: str) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    return tuple(sorted(PLACEHOLDER_CURLY.findall(s))), tuple(sorted(PLACEHOLDER_PRINTF.findall(s)))


def _read_strings(path: Path) -> Tuple[Dict[str, str], List[str]]:
    mapping: Dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        m = LINE_RE.match(line)
        if not m:
            continue
        mapping[m.group("key")] = _ios_unescape(m.group("val"))
    return mapping, lines


def _write_strings(path: Path, original_lines: List[str], updated: Dict[str, str]) -> None:
    out_lines: List[str] = []
    for line in original_lines:
        m = LINE_RE.match(line)
        if not m:
            out_lines.append(line)
            continue
        key = m.group("key")
        if key not in updated:
            out_lines.append(line)
            continue
        val = _ios_escape(updated[key])
        out_lines.append(f"\"{key}\" = \"{val}\";")
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


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
    items: List[Tuple[str, str]],
    lang_name: str,
    do_not_translate_terms: list[str],
) -> Dict[str, str]:
    if not items:
        return {}

    batch_text = "\n".join(f"{k}: {v}" for k, v in items)
    brand_line = ""
    if do_not_translate_terms:
        brand_line = "\n4. Do NOT translate these terms: " + ", ".join(f'"{t}"' for t in do_not_translate_terms)

    system_prompt = f"""You are a professional translator specializing in mobile app localization.
Translate the following iOS Localizable.strings values from English to {lang_name}.

CRITICAL RULES:
1. Preserve ALL placeholders exactly, including %@, %d, %1$@ and {{count}} style.
2. Return translations in format: KEY: translated value
3. Keep it natural and user-friendly for mobile apps{brand_line}
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": batch_text},
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    return _parse_kv_lines(resp.choices[0].message.content or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate iOS Localizable.strings resources")
    parser.add_argument("--runner-dir", default=None, help="iOS Runner directory (contains en.lproj/...)")
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
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit('Missing API key. Set env var "OPENAI_API_KEY" or pass --api-key.')

    runner_dir = Path(args.runner_dir) if args.runner_dir else (guess_ios_runner_dir(Path.cwd()) or None)
    if not runner_dir:
        raise SystemExit('Unable to auto-detect iOS Runner dir; pass "--runner-dir".')

    en_path = runner_dir / "en.lproj" / "Localizable.strings"
    if not en_path.exists():
        raise SystemExit(f"English Localizable.strings not found: {en_path}")

    do_not_translate_terms = uniq(split_csv(args.do_not_translate_terms))
    client = openai.OpenAI(api_key=api_key)
    en_map, _ = _read_strings(en_path)

    lang_names = {
        "ar": "Arabic",
        "bn": "Bengali",
        "de": "German",
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
        "zh-Hans": "Chinese (Simplified)",
        "zh-Hant": "Chinese (Traditional)",
    }

    total_translated = 0

    for lproj in sorted(runner_dir.glob("*.lproj")):
        if lproj.name == "en.lproj":
            continue
        strings_path = lproj / "Localizable.strings"
        if not strings_path.exists():
            continue

        locale = lproj.name.replace(".lproj", "")
        lang_name = lang_names.get(locale, locale)

        mapping, original_lines = _read_strings(strings_path)

        to_translate: List[Tuple[str, str]] = []
        for k, en_val in en_map.items():
            tgt_val = mapping.get(k)
            if tgt_val is None:
                continue
            if tgt_val != en_val:
                continue
            to_translate.append((k, en_val))

        if not to_translate:
            continue

        print(f"📂 iOS {lproj.name}: translating {len(to_translate)} strings...")

        batch_size = 20
        for i in range(0, len(to_translate), batch_size):
            batch = to_translate[i : i + batch_size]
            results = _translate_batch(client, args.model, batch, lang_name, do_not_translate_terms)
            for k, en_val in batch:
                if k not in results:
                    continue
                candidate = results[k]
                if _placeholders(en_val) != _placeholders(candidate):
                    continue
                mapping[k] = candidate
                total_translated += 1
            if i + batch_size < len(to_translate):
                time.sleep(1)

        _write_strings(strings_path, original_lines, mapping)

    print(f"✅ iOS strings translated: {total_translated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

