#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ATTR_PATTERN = re.compile(
    r'(android:(?:text|hint|contentDescription|title|summary))="([^"]*)"'
)


def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def slugify(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        return "symbol"
    return value[:42]


def load_existing_keys(values_dir: Path) -> set[str]:
    keys: set[str] = set()
    for file in values_dir.glob("strings*.xml"):
        try:
            root = ET.parse(file).getroot()
        except ET.ParseError:
            continue
        for child in root.findall("string"):
            name = child.attrib.get("name")
            if name:
                keys.add(name)
    return keys


def load_generated_entries(generated_file: Path) -> dict[str, tuple[str, bool]]:
    entries: dict[str, tuple[str, bool]] = {}
    if not generated_file.exists():
        return entries
    try:
        root = ET.parse(generated_file).getroot()
    except ET.ParseError:
        return entries
    for child in root.findall("string"):
        name = child.attrib.get("name")
        if not name:
            continue
        text = child.text or ""
        translatable = child.attrib.get("translatable", "true") != "false"
        entries[name] = (text, translatable)
    return entries


def has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def generate_key(base: str, reserved: set[str]) -> str:
    key = f"layout_auto_{base}"
    if key not in reserved:
        reserved.add(key)
        return key
    index = 2
    while True:
        candidate = f"{key}_{index}"
        if candidate not in reserved:
            reserved.add(candidate)
            return candidate
        index += 1


def write_generated(generated_file: Path, entries: dict[str, tuple[str, bool]]) -> None:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
    for key in sorted(entries.keys()):
        value, translatable = entries[key]
        if translatable:
            lines.append(f'    <string name="{key}">{xml_escape(value)}</string>')
        else:
            lines.append(
                f'    <string name="{key}" translatable="false">{xml_escape(value)}</string>'
            )
    lines.append("</resources>")
    generated_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract hardcoded layout text/hint/contentDescription/title/summary to strings XML"
    )
    parser.add_argument(
        "--res-dir",
        required=True,
        help="Android res directory (example: app/src/main/res)",
    )
    parser.add_argument(
        "--generated-file",
        default="strings_layout_auto.xml",
        help="Generated strings filename inside values/ (default: strings_layout_auto.xml)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    res_dir = Path(args.res_dir)
    layout_dir = res_dir / "layout"
    values_dir = res_dir / "values"
    generated_file = values_dir / args.generated_file

    if not layout_dir.exists():
        raise SystemExit(f"layout dir not found: {layout_dir}")
    if not values_dir.exists():
        raise SystemExit(f"values dir not found: {values_dir}")

    existing_keys = load_existing_keys(values_dir)
    generated_entries = load_generated_entries(generated_file)
    literal_to_key = {v: k for k, (v, _) in generated_entries.items()}

    total_replaced = 0
    changed_files = 0

    for file in sorted(layout_dir.glob("*.xml")):
        text = file.read_text(encoding="utf-8")

        def repl(match: re.Match[str]) -> str:
            nonlocal total_replaced
            attr, value = match.group(1), match.group(2)
            if not value or value.startswith("@") or value.startswith("?"):
                return match.group(0)
            if value == "@null":
                return match.group(0)
            key = literal_to_key.get(value)
            if key is None:
                key = generate_key(slugify(value), existing_keys)
                literal_to_key[value] = key
                generated_entries[key] = (value, has_letters(value))
            total_replaced += 1
            return f'{attr}="@string/{key}"'

        replaced = ATTR_PATTERN.sub(repl, text)
        if replaced != text:
            changed_files += 1
            file.write_text(replaced, encoding="utf-8")

    write_generated(generated_file, generated_entries)
    print(
        f"localized layout literals: replaced={total_replaced}, files_changed={changed_files}, "
        f"strings_total={len(generated_entries)}"
    )
    print(f"generated strings file: {generated_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
