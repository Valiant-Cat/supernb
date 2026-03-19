#!/usr/bin/env python3
"""
Translate Android string resources for values-*/strings.xml using OpenAI.

Policy:
- Use `values/strings.xml` as the English reference.
- For each `values-xx/strings.xml`, translate any value identical to English.
- Preserve placeholders:
  - {count} style
  - %s / %1$s / %d

Usage:
  export OPENAI_API_KEY="sk-..."
  python3 complete_android_strings_translations.py --res-dir path/to/android/app/src/main/res
"""

from __future__ import annotations

import argparse
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

import openai

from _path_guess import guess_android_res_dir, split_csv, uniq


PLACEHOLDER_CURLY = re.compile(r"\{(\w+)\}")
PLACEHOLDER_PRINTF = re.compile(r"%(?:\d+\\$)?[sdfox]")  # %s, %1$s, %d, etc.
UNESCAPED_APOSTROPHE = re.compile(r"(?<!\\)'")
UNESCAPED_QUOTE = re.compile(r'(?<!\\)"')


def _android_escape(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = UNESCAPED_APOSTROPHE.sub(r"\\'", s)
    s = UNESCAPED_QUOTE.sub(r'\\"', s)
    return s


def _placeholders(s: str) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    return tuple(sorted(PLACEHOLDER_CURLY.findall(s))), tuple(sorted(PLACEHOLDER_PRINTF.findall(s)))


def _read_strings_xml(path: Path) -> Dict[str, str]:
    tree = ET.parse(path)
    root = tree.getroot()
    out: Dict[str, str] = {}
    for child in root:
        if child.tag != "string":
            continue
        name = child.attrib.get("name")
        if not name:
            continue
        out[name] = (child.text or "")
    return out


def _write_strings_xml(path: Path, values: Dict[str, str]) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    for child in root:
        if child.tag != "string":
            continue
        name = child.attrib.get("name")
        if not name or name not in values:
            continue
        child.text = values[name]
    tree.write(path, encoding="utf-8", xml_declaration=True)


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
Translate the following Android string resource values from English to {lang_name}.

CRITICAL RULES:
1. Preserve ALL placeholders exactly, including {{count}} style and printf tokens like %s, %1$s, %d
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
    parser = argparse.ArgumentParser(description="Translate Android strings.xml resources")
    parser.add_argument("--res-dir", default=None, help="Android res directory (contains values/strings.xml)")
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

    res_dir = Path(args.res_dir) if args.res_dir else (guess_android_res_dir(Path.cwd()) or None)
    if not res_dir:
        raise SystemExit('Unable to auto-detect Android res dir; pass "--res-dir".')

    base_path = res_dir / "values" / "strings.xml"
    if not base_path.exists():
        raise SystemExit(f"Base strings.xml not found: {base_path}")

    do_not_translate_terms = uniq(split_csv(args.do_not_translate_terms))
    client = openai.OpenAI(api_key=api_key)
    base = _read_strings_xml(base_path)

    # Map Android qualifier to language name for prompt (fallback to qualifier).
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
        "zh": "Chinese (Simplified)",
    }

    total_translated = 0

    for values_dir in sorted(res_dir.glob("values-*")):
        strings_path = values_dir / "strings.xml"
        if not strings_path.exists():
            continue

        qualifier = values_dir.name.split("-", 1)[1]
        lang_name = lang_names.get(qualifier, qualifier)

        data = _read_strings_xml(strings_path)
        to_translate: List[Tuple[str, str]] = []
        for k, en_val in base.items():
            tgt_val = data.get(k)
            if tgt_val is None:
                continue
            if tgt_val != en_val:
                continue
            to_translate.append((k, en_val))

        if not to_translate:
            continue

        print(f"📂 Android {values_dir.name}: translating {len(to_translate)} strings...")

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
                data[k] = _android_escape(candidate)
                total_translated += 1
            if i + batch_size < len(to_translate):
                time.sleep(1)

        _write_strings_xml(strings_path, data)

    print(f"✅ Android strings translated: {total_translated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

