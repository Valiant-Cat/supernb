#!/usr/bin/env python3
"""
Sync ARB keys from the English reference into all other locales.

Goal:
- Ensure every `*.arb` in the l10n directory contains all string keys from the base ARB.
- For missing keys, fill with the base value as a placeholder.
- Never overwrite existing translations.

Usage:
  python3 sync_arb_placeholders.py --l10n-dir path/to/lib/l10n

Notes:
- Default l10n dir is guessed from current working directory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _path_guess import guess_l10n_dir


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: dict) -> None:
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

    arbs = sorted(l10n_dir.glob("*.arb"))
    if not arbs:
        raise SystemExit(f"No .arb files found under: {l10n_dir}")
    return arbs[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync missing ARB keys from base language")
    parser.add_argument(
        "--l10n-dir",
        default=None,
        help="Path to directory containing *.arb files (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--base-arb",
        default=None,
        help="Base ARB filename inside l10n dir (default: app_en.arb, *_en.arb, or first *.arb)",
    )
    args = parser.parse_args()

    l10n_dir = Path(args.l10n_dir) if args.l10n_dir else (guess_l10n_dir(Path.cwd()) or None)
    if not l10n_dir:
        raise SystemExit('Unable to auto-detect l10n dir; pass "--l10n-dir".')

    l10n_dir = Path(l10n_dir)
    if not l10n_dir.exists():
        raise SystemExit(f"l10n dir not found: {l10n_dir}")

    base_path = _pick_base_arb(l10n_dir, args.base_arb)
    base = _load(base_path)
    ref_keys = [k for k in base.keys() if not k.startswith("@")]

    updated_files = 0
    total_added = 0

    for arb_path in sorted(l10n_dir.glob("*.arb")):
        if arb_path == base_path:
            continue

        data = _load(arb_path)
        added = 0

        for key in ref_keys:
            if key not in data:
                value = base.get(key)
                if isinstance(value, str):
                    data[key] = value
                    added += 1

        if added:
            _save(arb_path, data)
            updated_files += 1
            total_added += added

    print(f"Synced ARB placeholders: {updated_files} files updated, {total_added} keys added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

