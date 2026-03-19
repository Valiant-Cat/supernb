#!/usr/bin/env python3
"""
Identify missing/untranslated strings in ARB files within an l10n directory.

Default policy:
- Base file is `app_en.arb` (or the first `*_en.arb` found).
- A target entry "needs translation" if:
  - missing key, non-string value, or
  - value equals base (English) exactly (unless allowed).

Usage:
  python3 check_arb_translation_gaps.py --l10n-dir path/to/lib/l10n
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from _path_guess import guess_l10n_dir, split_csv, uniq


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def _string_keys(data: dict[str, Any]) -> list[str]:
    return [k for k in data.keys() if not k.startswith("@") and isinstance(data.get(k), str)]


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


def _locale_from_filename(path: Path) -> str:
    # app_zh.arb -> zh ; intl_en.arb -> en
    stem = path.stem
    if "_" in stem:
        return stem.rsplit("_", 1)[1]
    return stem


def _print_preview(
    missing: list[str],
    *,
    base: dict[str, Any],
    target: dict[str, Any],
    target_locale: str,
    preview_count: int,
) -> None:
    for i, key in enumerate(missing[:preview_count]):
        base_preview = str(base.get(key, ""))[:90]
        tgt_val = target.get(key)
        tgt_preview = "[MISSING]" if tgt_val is None else str(tgt_val)[:90]
        print(f"  {i + 1}. {key}")
        print(f"     BASE: {base_preview}")
        print(f"     {target_locale.upper()}: {tgt_preview}")
        print()


def _iter_targets(l10n_dir: Path, base_path: Path) -> Iterable[Path]:
    for p in sorted(l10n_dir.glob("*.arb")):
        if p == base_path:
            continue
        yield p


def main() -> int:
    parser = argparse.ArgumentParser(description="Check missing/untranslated ARB strings")
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
    parser.add_argument("--preview", type=int, default=5, help="Preview N missing keys per locale")
    args = parser.parse_args()

    l10n_dir = Path(args.l10n_dir) if args.l10n_dir else (guess_l10n_dir(Path.cwd()) or None)
    if not l10n_dir:
        raise SystemExit('Unable to auto-detect l10n dir; pass "--l10n-dir".')

    base_path = _pick_base_arb(l10n_dir, args.base_arb)
    base = _load_json(base_path)
    keys = _string_keys(base)

    treat_same_as_base = args.treat_same_as_base.lower() == "true"
    allow_unchanged_keys = set(uniq(split_csv(args.allow_unchanged_keys)))
    allow_unchanged_values = set(uniq(split_csv(args.allow_unchanged_values)))

    print("IDENTIFYING MISSING TRANSLATIONS")
    print("=" * 80)
    print(f"l10n dir : {l10n_dir}")
    print(f"base ARB : {base_path.name}")
    print("=" * 80)

    totals: dict[str, int] = {}
    for target_path in _iter_targets(l10n_dir, base_path):
        locale = _locale_from_filename(target_path)
        target = _load_json(target_path)
        missing: list[str] = []

        for key in keys:
            if _needs_translation(
                base.get(key),
                target.get(key),
                key,
                treat_same_as_base=treat_same_as_base,
                allow_unchanged_keys=allow_unchanged_keys,
                allow_unchanged_values=allow_unchanged_values,
            ):
                missing.append(key)

        totals[locale] = len(missing)
        if missing:
            progress = (len(keys) - len(missing)) / max(len(keys), 1) * 100
            print(f"\n{locale}: {progress:.1f}% complete - {len(missing)} missing/untranslated")
            print("-" * 60)
            _print_preview(
                missing,
                base=base,
                target=target,
                target_locale=locale,
                preview_count=max(0, args.preview),
            )
            if len(missing) > args.preview:
                print(f"  ... and {len(missing) - args.preview} more\n")
        else:
            print(f"✅ {locale}: 100% complete - no missing/untranslated strings")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_missing = 0
    for locale in sorted(totals.keys()):
        total_missing += totals[locale]
        print(f"{locale:<12}: {totals[locale]:>4} missing")
    print("-" * 80)
    print(f"{'TOTAL':<12}: {total_missing:>4} missing across all locales")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

