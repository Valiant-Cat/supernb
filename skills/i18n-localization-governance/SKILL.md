---
name: i18n-localization-governance
description: Use when the user wants localization, translation, multi-language support, extraction of hardcoded user-facing strings, or enforcement that copy stays out of source code for app or web projects.
---

# I18n Localization Governance

This skill enforces localization as an implementation rule, not a late cleanup pass.

## Core Rule

User-facing copy must not be hardcoded in product code.

That includes:

- app UI strings
- web UI strings
- labels
- buttons
- empty states
- error messages
- onboarding copy

## Routing Rules

- For Flutter projects, use the local `flutter-l10n-translation` workflow when translation or ARB maintenance is needed.
- For Android projects, use the local `android-i18n-translation` workflow when extracting hardcoded strings or maintaining `strings.xml` locales.
- For other stacks, enforce the same externalization principle using the project’s localization layer or resource files.
- Prefer the stack-specific guidance in `docs/i18n-stack-guidance.md` when this repo is available locally.

## Minimum Workflow

1. Find or define the localization resource layer.
2. Extract any hardcoded user-facing strings out of code.
3. Add new keys in the source locale first.
4. Sync target locales.
5. Fill translations with the relevant local translation workflow when available.
6. Verify that the implementation reads strings from localization resources, not inline literals.
7. Run the hardcoded-copy check when the workspace provides it.

## Stack Awareness

- Flutter and Android have explicit local translation workflows available in this environment.
- iOS, web, and mixed-stack projects still follow the same no-hardcoded-copy rule even when the exact toolchain differs.
- The goal is consistent localization governance across stacks, not a one-framework-only solution.

## Shipping Rule

Localization readiness is part of release readiness. Missing extraction or untranslated core flows should block completion for multi-language products.
