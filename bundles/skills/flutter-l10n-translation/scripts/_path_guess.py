from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional


def _is_ignored_dir(path: Path) -> bool:
    parts = set(path.parts)
    return any(
        p in parts
        for p in [
            ".git",
            ".dart_tool",
            "build",
            ".idea",
            ".vscode",
            "node_modules",
        ]
    )


def guess_l10n_dir(cwd: Path) -> Optional[Path]:
    candidates = [
        cwd / "lib" / "l10n",
        cwd / "lib" / "l10n",
        cwd / "l10n",
    ]
    for c in candidates:
        if (c / "app_en.arb").exists():
            return c
        if c.exists() and any(c.glob("*.arb")):
            return c

    # Monorepo / packages: find the first directory containing app_en.arb.
    for p in cwd.rglob("app_en.arb"):
        if _is_ignored_dir(p):
            continue
        return p.parent

    for p in cwd.rglob("*.arb"):
        if _is_ignored_dir(p):
            continue
        return p.parent

    return None


def guess_android_res_dir(cwd: Path) -> Optional[Path]:
    candidates = [
        cwd / "android" / "app" / "src" / "main" / "res",
        cwd / "android" / "app" / "src" / "main" / "res",
    ]
    for c in candidates:
        if (c / "values" / "strings.xml").exists():
            return c

    for p in cwd.rglob("android/app/src/main/res/values/strings.xml"):
        if _is_ignored_dir(p):
            continue
        return p.parent.parent
    return None


def guess_ios_runner_dir(cwd: Path) -> Optional[Path]:
    candidates = [
        cwd / "ios" / "Runner",
        cwd / "ios" / "Runner",
    ]
    for c in candidates:
        if (c / "en.lproj" / "Localizable.strings").exists():
            return c

    for p in cwd.rglob("ios/Runner/en.lproj/Localizable.strings"):
        if _is_ignored_dir(p):
            continue
        return p.parent.parent
    return None


def split_csv(values: Optional[str]) -> list[str]:
    if not values:
        return []
    return [v.strip() for v in values.split(",") if v.strip()]


def uniq(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out

