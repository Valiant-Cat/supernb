# I18n Stack Guidance

This document explains how `supernb` should enforce localization across common stacks.

The universal rule is unchanged:

- user-facing copy must not be hardcoded in product code
- source locale comes first
- target locales are synced after source keys exist
- release readiness includes localization checks

## 1. Flutter

Preferred pattern:

- ARB files under `lib/l10n/`
- generated localization accessors via `gen-l10n`
- optional platform resource sync for Android and iOS

`supernb` guidance:

- add new copy to the source ARB first
- preserve `@key` metadata and ICU placeholders
- use the local `flutter-l10n-translation` workflow for gap checks and translation completion
- avoid inline text in widgets unless it is clearly non-user-facing and explicitly exempted

## 2. Native Android

Preferred pattern:

- `res/values/strings.xml` as source locale
- `values-*` locale folders for translations
- layout XML and code referencing `@string/...`

`supernb` guidance:

- extract hardcoded layout text into `strings.xml`
- use the local `android-i18n-translation` workflow when appropriate
- keep placeholders stable across locales
- validate with resource merge and lint before release

## 3. Native iOS

Preferred pattern:

- `.strings` or `.xcstrings` resources as the source of truth
- UI code referencing localized resources instead of raw copy

`supernb` guidance:

- avoid inline copy in SwiftUI or UIKit when the text is user-facing
- store source strings in the project’s localization resource layer first
- keep formatting tokens and interpolation variables stable across locales

## 4. Web Apps

Preferred pattern:

- locale resources under a dedicated `locales/`, `messages/`, or `i18n/` directory
- framework-level translation helpers used in components

Examples:

- Next.js: framework or library-backed message catalogs
- React: resource dictionaries plus translation hook
- Vue: locale message bundles plus translation helper
- Svelte: externalized message stores or locale dictionaries

`supernb` guidance:

- do not embed visible UI copy directly in components when a localization layer exists or should exist
- put product copy into locale resources first
- ensure components read from translation helpers or message lookups
- consider text expansion and locale-specific layout shifts during design review

## 5. Backend And Service Surfaces

Preferred pattern:

- user-facing API error messages, emails, notifications, and templates should come from managed message resources or template files

`supernb` guidance:

- keep operational or developer-only strings separate from end-user copy
- externalize email, notification, and customer-facing message bodies
- if the backend drives app or web copy, those messages still count as localized product copy

## 6. Mixed-Stack Products

Many products combine:

- web frontend
- mobile app
- backend notifications
- marketing or onboarding surfaces

`supernb` guidance:

- define the source-locale strategy once in the PRD and implementation plan
- avoid each surface inventing its own copy source independently
- document where localization truth lives for each layer

## 7. Exemptions

Not every literal string should block release.

Potential exemptions:

- debug logging
- internal developer diagnostics
- test fixtures
- generated code
- explicit `supernb-ignore-hardcoded-copy` cases

But do not abuse exemptions for visible product copy.

