---
name: flutter-l10n-translation
description: Flutter i18n/l10n ARB 多语言翻译工作流：同步 ARB key、检查缺失/未翻译字符串、用 OpenAI 自动补全翻译并严格保留 ICU/占位符；可选翻译 Android strings.xml 与 iOS Localizable.strings。
metadata:
  short-description: Flutter ARB 多语言翻译
---

# Flutter 多语言翻译（ARB / gen-l10n）

目标：把 Flutter 工程里的 `*.arb`（以及可选的原生资源）翻译补齐，同时保证：
- key 不变、`@key` 元数据不丢
- ICU MessageFormat / 占位符不被破坏（如 `{count}`、`{count, plural, ...}`、`%s`、`%@`）
- 仅翻译“缺失/疑似未翻译”的条目（默认：目标值缺失/类型不对/与英文完全相同）

## 使用前需要确认（让 Agent 问你/或自动推断）

- **l10n 目录**：包含 `*.arb` 的目录（常见：`lib/l10n/`、`lib/l10n/`、`packages/*/lib/l10n/`）
- **英文基准文件**：通常是 `app_en.arb`（或任意 `*_en.arb`）
- **不翻译词**：产品名/品牌名/缩写（例如 app 名、iOS/Android/URL 等）
- **覆盖范围**：只补缺失 vs 允许覆盖已有翻译（默认只补缺失/未翻译）

## 推荐工作流（默认顺序）

1) **同步 key（可选但强烈推荐）**
   - 新增 key 时先改英文基准 ARB（并补齐 `@key` 描述/占位符元信息）
   - 再把其它语言缺失的 key 先用英文占位填充（避免运行期找不到 key）

2) **检查缺失/未翻译**
   - 输出每个 locale 的缺失数量、完成度、以及缺失 key 预览

3) **AI 翻译补全（写回 ARB）**
   - 批量翻译缺失/与英文相同的字符串
   - 校验 ICU/占位符变量集合一致；不一致则跳过该条

4) **（可选）翻译原生通知资源**
   - Android：`android/**/res/values-*/strings.xml`
   - iOS：`ios/**/Runner/*.lproj/Localizable.strings`

5) **生成/测试**
   - `flutter gen-l10n`
   - `flutter test` / `flutter analyze`
   - RTL 冒烟（阿语/波斯语/乌尔都语）

## 直接可用的脚本（从项目根目录运行）

先解析当前安装的 skill 目录：

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

FLUTTER_L10N_SKILL_DIR="$(resolve_skill_dir flutter-l10n-translation)"
```

安装依赖：
```bash
python3 -m pip install -r "$FLUTTER_L10N_SKILL_DIR/scripts/requirements_translation.txt"
```

同步缺失 key（把缺失 key 用英文占位补齐）：
```bash
python3 "$FLUTTER_L10N_SKILL_DIR/scripts/sync_arb_placeholders.py" --l10n-dir path/to/lib/l10n
```

检查缺口：
```bash
python3 "$FLUTTER_L10N_SKILL_DIR/scripts/check_arb_translation_gaps.py" --l10n-dir path/to/lib/l10n
```

AI 补全翻译（写回 ARB）：
```bash
export OPENAI_API_KEY="sk-..."  # 或在 shell 环境里配置
python3 "$FLUTTER_L10N_SKILL_DIR/scripts/complete_arb_translations_direct.py" \
  --l10n-dir path/to/lib/l10n \
  --model gpt-4o-mini
```

（可选）Android strings.xml：
```bash
export OPENAI_API_KEY="sk-..."
python3 "$FLUTTER_L10N_SKILL_DIR/scripts/complete_android_strings_translations.py" \
  --res-dir path/to/android/app/src/main/res
```

（可选）iOS Localizable.strings：
```bash
export OPENAI_API_KEY="sk-..."
python3 "$FLUTTER_L10N_SKILL_DIR/scripts/complete_ios_localizable_strings_translations.py" \
  --runner-dir path/to/ios/Runner
```

## Agent 执行守则（重要）

- **永远先改英文基准 ARB**：新增功能文案时，先在英文文件里加 key + `@key` 描述 + placeholders（如果有）。
- **禁止改占位符变量名**：`{count}`、`{app}`、`{count, plural, ...}` 里的 `count/app` 必须保持原样。
- **禁止翻译 key / 元数据 key**：只改字符串 value，不动 `@...`、`@@...`。
- **先检查再写回**：先跑 gap 检查，翻译后再跑一次检查做回归。
- **低风险优先**：默认只翻译缺失/未翻译（与英文相同）的条目；如要覆盖已有翻译必须征得用户确认。
