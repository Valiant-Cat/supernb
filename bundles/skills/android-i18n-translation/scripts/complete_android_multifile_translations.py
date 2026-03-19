#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import xml.etree.ElementTree as ET

import openai
from deep_translator import GoogleTranslator


PLACEHOLDER_CURLY = re.compile(r"\{(\w+)\}")
PLACEHOLDER_PRINTF = re.compile(r"%(?:\d+\$)?[sdfox]")
FORCE_TRANSLATE_KEYS = {
    "features_screen_title",
    "features_screen_subtitle",
    "permissions_screen_title",
    "permissions_screen_subtitle",
    "feature_flashlight_subtitle",
    "feature_scan_create_title",
    "feature_scan_create_subtitle",
    "feature_magnify_subtitle",
    "feature_remote_title",
    "feature_remote_subtitle",
    "feature_games_title",
    "feature_games_subtitle",
    "feature_wallpapers_title",
    "feature_wallpapers_subtitle",
    "feature_notes_subtitle",
    "permission_background_location_title",
    "permission_background_location_subtitle",
    "permission_coarse_location_title",
    "permission_coarse_location_subtitle",
    "permission_fine_location_title",
    "permission_fine_location_subtitle",
    "permission_network_title",
    "permission_network_subtitle",
    "permission_wifi_title",
    "permission_wifi_subtitle",
    "permission_camera_subtitle",
    "weather_no_data_available",
    "battery_health_good",
    "battery_health_overheat",
    "battery_health_dead",
    "battery_health_over_voltage",
    "battery_health_unspecified_failure",
    "battery_health_cold",
    "battery_health_unknown",
    "pet_network_weak_hint",
    "speech_recognition_unavailable",
    "speech_recognition_failed_format",
    "long_speech_recognition_unavailable",
    "long_speech_recognition_failed_format",
    "pet_yawn_effect_text",
}


@dataclass
class StringEntry:
    name: str
    text: str
    translatable: bool = True


def parse_strings_xml(path: Path) -> "OrderedDict[str, StringEntry]":
    result: "OrderedDict[str, StringEntry]" = OrderedDict()
    if not path.exists():
        return result
    root = ET.parse(path).getroot()
    for child in root:
        if child.tag != "string":
            continue
        name = child.attrib.get("name")
        if not name:
            continue
        translatable = child.attrib.get("translatable", "true") != "false"
        result[name] = StringEntry(name=name, text=child.text or "", translatable=translatable)
    return result


def write_strings_xml(path: Path, entries: "OrderedDict[str, StringEntry]") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
    for _, entry in entries.items():
        txt = (
            entry.text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        if entry.translatable:
            lines.append(f'    <string name="{entry.name}">{txt}</string>')
        else:
            lines.append(
                f'    <string name="{entry.name}" translatable="false">{txt}</string>'
            )
    lines.append("</resources>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def placeholders(text: str) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    return (
        tuple(sorted(PLACEHOLDER_CURLY.findall(text))),
        tuple(sorted(PLACEHOLDER_PRINTF.findall(text))),
    )


def qualifier_to_lang(values_dir_name: str) -> str:
    q = values_dir_name.replace("values-", "", 1)
    return q.split("-r", 1)[0]


def qualifier_to_prompt_lang(values_dir_name: str) -> str:
    q = values_dir_name.replace("values-", "", 1)
    mapping = {
        "ar": "Arabic",
        "am": "Amharic",
        "bg": "Bulgarian",
        "bn": "Bengali",
        "ca": "Catalan",
        "cs": "Czech",
        "da": "Danish",
        "de": "German",
        "el": "Greek",
        "en": "English",
        "es": "Spanish",
        "et": "Estonian",
        "fa": "Persian",
        "fi": "Finnish",
        "fil": "Filipino",
        "fr": "French",
        "gu": "Gujarati",
        "ha": "Hausa",
        "hi": "Hindi",
        "hr": "Croatian",
        "hu": "Hungarian",
        "in": "Indonesian",
        "it": "Italian",
        "iw": "Hebrew",
        "ja": "Japanese",
        "km": "Khmer",
        "kn": "Kannada",
        "ko": "Korean",
        "ku": "Kurdish",
        "lo": "Lao",
        "lt": "Lithuanian",
        "lv": "Latvian",
        "ml": "Malayalam",
        "mr": "Marathi",
        "ms": "Malay",
        "my": "Burmese",
        "nb": "Norwegian Bokmal",
        "nl": "Dutch",
        "pa": "Punjabi",
        "pl": "Polish",
        "pt": "Portuguese",
        "ro": "Romanian",
        "ru": "Russian",
        "sk": "Slovak",
        "sl": "Slovenian",
        "sr": "Serbian",
        "sv": "Swedish",
        "sw": "Swahili",
        "ta": "Tamil",
        "te": "Telugu",
        "th": "Thai",
        "tr": "Turkish",
        "uk": "Ukrainian",
        "ur": "Urdu",
        "vi": "Vietnamese",
        "yo": "Yoruba",
        "zh": "Chinese",
    }
    lang = qualifier_to_lang(values_dir_name)
    base = mapping.get(lang, lang)
    if q == "zh-rTW":
        return "Chinese (Traditional, Taiwan)"
    if q == "zh-rCN":
        return "Chinese (Simplified, China)"
    return f"{base} ({q})"


def parse_kv_lines(content: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (content or "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def translate_batch(
    client: openai.OpenAI,
    model: str,
    items: List[Tuple[str, str]],
    prompt_lang: str,
) -> Dict[str, str]:
    if not items:
        return {}

    body = "\n".join(f"{k}: {v}" for k, v in items)
    sys_prompt = f"""You are a professional mobile app translator.
Translate the following Android string values into {prompt_lang}.

Rules:
1. Keep KEY unchanged, return lines in 'KEY: translated value' format.
2. Preserve placeholders exactly, including {{name}}, %s, %1$s, %d.
3. Preserve newline escapes like \\n.
4. Keep short UI style, natural and clear.
"""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": body},
        ],
        temperature=0.2,
        max_tokens=3000,
    )
    return parse_kv_lines(resp.choices[0].message.content or "")


GOOGLE_LANG_MAP = {
    "am": "am",
    "ar": "ar",
    "bg": "bg",
    "bn": "bn",
    "ca": "ca",
    "cs": "cs",
    "da": "da",
    "de": "de",
    "el": "el",
    "en": "en",
    "es": "es",
    "et": "et",
    "fa": "fa",
    "fi": "fi",
    "fil": "tl",
    "fr": "fr",
    "gu": "gu",
    "ha": "ha",
    "hi": "hi",
    "hr": "hr",
    "hu": "hu",
    "in": "id",
    "it": "it",
    "iw": "iw",
    "ja": "ja",
    "km": "km",
    "kn": "kn",
    "ko": "ko",
    "ku": "ku",
    "lo": "lo",
    "lt": "lt",
    "lv": "lv",
    "ml": "ml",
    "mr": "mr",
    "ms": "ms",
    "my": "my",
    "nb": "no",
    "nl": "nl",
    "pa": "pa",
    "pl": "pl",
    "pt": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl": "sl",
    "sr": "sr",
    "sv": "sv",
    "sw": "sw",
    "ta": "ta",
    "te": "te",
    "th": "th",
    "tr": "tr",
    "uk": "uk",
    "ur": "ur",
    "vi": "vi",
    "yo": "yo",
    "zh": "zh-CN",
}


def protect_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    tokens: Dict[str, str] = {}
    output = text
    all_ph = list(dict.fromkeys(PLACEHOLDER_CURLY.findall(text)))
    idx = 0
    for name in all_ph:
        raw = "{" + name + "}"
        token = f"__PH_{idx}__"
        output = output.replace(raw, token)
        tokens[token] = raw
        idx += 1

    for match in dict.fromkeys(PLACEHOLDER_PRINTF.findall(output)):
        token = f"__PH_{idx}__"
        output = output.replace(match, token)
        tokens[token] = match
        idx += 1

    if "\\n" in output:
        token = f"__PH_{idx}__"
        output = output.replace("\\n", token)
        tokens[token] = "\\n"

    return output, tokens


def unprotect_placeholders(text: str, tokens: Dict[str, str]) -> str:
    output = text
    for token, raw in tokens.items():
        output = output.replace(token, raw)
    return output


def translate_batch_google(items: List[Tuple[str, str]], lang_code: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    target = GOOGLE_LANG_MAP.get(lang_code, lang_code)
    try:
        translator = GoogleTranslator(source="en", target=target)
    except Exception:
        for key, source in items:
            out[key] = source
        return out
    protected_texts: List[str] = []
    tokens_list: List[Dict[str, str]] = []
    keys: List[str] = []
    sources: List[str] = []

    for key, source in items:
        protected, tokens = protect_placeholders(source)
        keys.append(key)
        sources.append(source)
        protected_texts.append(protected)
        tokens_list.append(tokens)

    translated_list: List[str] = []
    try:
        batch_result = translator.translate_batch(protected_texts)
        if isinstance(batch_result, list):
            translated_list = [item if isinstance(item, str) else "" for item in batch_result]
    except Exception:
        translated_list = []

    if len(translated_list) != len(items):
        translated_list = []
        for protected, source in zip(protected_texts, sources):
            try:
                item = translator.translate(protected)
            except Exception:
                item = source
            translated_list.append(item or source)

    for key, source, translated, tokens in zip(keys, sources, translated_list, tokens_list):
        candidate = unprotect_placeholders(translated or source, tokens)
        out[key] = candidate
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete Android translations for all strings*.xml files")
    parser.add_argument("--res-dir", required=True, help="Android res directory")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--provider", choices=["auto", "openai", "google"], default="auto")
    parser.add_argument("--sleep-seconds", type=float, default=0.6)
    args = parser.parse_args()

    res_dir = Path(args.res_dir)
    values_dir = res_dir / "values"
    if not values_dir.exists():
        raise SystemExit(f"values dir not found: {values_dir}")

    base_files = sorted(p.name for p in values_dir.glob("strings*.xml"))
    if not base_files:
        raise SystemExit("No base strings*.xml files found in values/")

    base_by_file: Dict[str, "OrderedDict[str, StringEntry]"] = {
        file_name: parse_strings_xml(values_dir / file_name) for file_name in base_files
    }

    target_dirs = sorted(
        d for d in res_dir.glob("values-*")
        if d.is_dir() and d.name != "values-night"
    )

    lang_to_dirs: Dict[str, List[Path]] = {}
    for d in target_dirs:
        lang_to_dirs.setdefault(qualifier_to_lang(d.name), []).append(d)

    total_added = 0
    total_copied = 0
    translation_jobs: List[Tuple[Path, str, List[Tuple[str, str]]]] = []

    for target_dir in target_dirs:
        lang = qualifier_to_lang(target_dir.name)
        peer_dirs = [d for d in lang_to_dirs.get(lang, []) if d != target_dir]

        for file_name in base_files:
            base_entries = base_by_file[file_name]
            target_path = target_dir / file_name
            target_entries = parse_strings_xml(target_path)

            changed = False
            to_translate: List[Tuple[str, str]] = []
            added_keys: set[str] = set()

            for key, base_entry in base_entries.items():
                current = target_entries.get(key)
                if current is None:
                    copied = None
                    for peer in peer_dirs:
                        peer_entries = parse_strings_xml(peer / file_name)
                        peer_entry = peer_entries.get(key)
                        if peer_entry and peer_entry.text:
                            copied = peer_entry
                            break
                    if copied is not None:
                        target_entries[key] = StringEntry(
                            name=key,
                            text=copied.text,
                            translatable=base_entry.translatable,
                        )
                        total_copied += 1
                    else:
                        target_entries[key] = StringEntry(
                            name=key,
                            text=base_entry.text,
                            translatable=base_entry.translatable,
                        )
                        added_keys.add(key)
                        total_added += 1
                    changed = True

                tgt_entry = target_entries[key]
                if not base_entry.translatable:
                    tgt_entry.translatable = False
                    continue

                if target_dir.name.startswith("values-en"):
                    continue

                if tgt_entry.text.strip() == base_entry.text.strip() and any(ch.isalpha() for ch in base_entry.text):
                    if key in added_keys or key.startswith("layout_auto_") or key in FORCE_TRANSLATE_KEYS:
                        to_translate.append((key, base_entry.text))

            if changed:
                write_strings_xml(target_path, target_entries)

            if to_translate:
                translation_jobs.append((target_path, target_dir.name, to_translate))

    provider = args.provider
    client = openai.OpenAI(api_key=args.api_key) if args.api_key else None
    translated_count = 0
    openai_failed = False

    for target_path, qualifier_name, items in translation_jobs:
        entries = parse_strings_xml(target_path)
        lang_prompt = qualifier_to_prompt_lang(qualifier_name)
        lang_code = qualifier_to_lang(qualifier_name)
        batch_size = 25
        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            translated: Dict[str, str]
            use_google = provider == "google" or openai_failed or (provider == "auto" and client is None)
            if use_google:
                translated = translate_batch_google(batch, lang_code)
            else:
                try:
                    assert client is not None
                    translated = translate_batch(client, args.model, batch, lang_prompt)
                except Exception:
                    if provider == "openai":
                        raise
                    openai_failed = True
                    translated = translate_batch_google(batch, lang_code)
            for key, source in batch:
                candidate = translated.get(key)
                if not candidate:
                    continue
                if placeholders(source) != placeholders(candidate):
                    continue
                entries[key].text = candidate
                translated_count += 1
            if start + batch_size < len(items):
                time.sleep(args.sleep_seconds)
        write_strings_xml(target_path, entries)

    print(
        f"done: base_files={len(base_files)}, locales={len(target_dirs)}, "
        f"added={total_added}, copied_from_peer={total_copied}, translated={translated_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
