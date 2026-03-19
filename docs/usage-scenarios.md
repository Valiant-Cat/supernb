# Usage Scenarios

This file turns the main `supernb` modes into concrete prompts you can use directly.

Examples here are illustrative only. `supernb` is not tied to Flutter, Android, or any specific framework.

## 1. Full Product Delivery

Example:

```text
Use supernb to build me a commercial-grade expense tracking product.
Target platform, framework, and stack are described in the task itself.
It must support the required languages and markets I specify.
Do not stop at MVP quality.
Use this remote repository: <repo-url>
```

Expected mode:

- `full-product-delivery`
- `product-research-prd`
- `ui-ux-governance`
- `autonomous-delivery`

What `supernb` should do:

- create initiative artifacts
- research competitors and reviews
- write a PRD
- define UI/UX
- implement in batches
- commit continuously

Possible user-specified stack inputs:

- Flutter
- React Native
- native Android
- native iOS
- Next.js
- Django
- Go backend plus web frontend

## 2. Brainstorm And Save

Example:

```text
Use supernb to brainstorm an AI travel planner product and save the output locally.
```

Expected mode:

- `brainstorm-and-save`

What `supernb` should do:

- clarify the idea
- explore options
- recommend a direction
- save the result into local markdown artifacts

## 3. UI UX Upgrade For Existing Project

Example:

```text
Use supernb to upgrade the full UI/UX of my local project.
Keep the product intent, but make the interface commercial-grade and fix current readability and contrast issues.
```

Expected mode:

- `ui-ux-upgrade`
- `ui-ux-governance`

What `supernb` should do:

- inspect the project
- define upgrade direction
- implement changes
- run a final design audit

## 4. Implementation Only

Example:

```text
Use supernb to implement the billing module in my current repository.
Plan it, write tests, implement it, verify it, and commit the validated work.
```

Expected mode:

- `implementation-execution`
- `autonomous-delivery`

What `supernb` should do:

- inspect current code
- write a bounded plan
- implement and verify
- commit the result

## 5. Any Single Upstream Capability

Example:

```text
Use supernb to audit my frontend, harden the UX edge cases, and polish the final interactions.
```

Or:

```text
Use supernb to run competitor review mining for this app category and save the insights locally.
```

Or:

```text
Use supernb to debug this flaky test, verify the fix, and review the final patch.
```

Expected mode:

- `single-capability-router`

What `supernb` should do:

- identify the narrowest matching upstream capability
- use that capability directly
- save artifacts if the request expects persistent output

## 6. Localization And Translation

Example:

```text
Use supernb to remove hardcoded UI copy from my project, wire it into the localization system, and complete the required translations.
```

Expected mode:

- `i18n-localization-governance`
- `single-capability-router`

What `supernb` should do:

- find the localization layer
- extract hardcoded copy out of code
- add source-locale keys
- sync and complete target locales
- verify the UI reads from localization resources

## Operating Principle

The user may ask for "one shot" output, but `supernb` should still distinguish between:

- full product delivery
- product strategy and documentation only
- UI/UX upgrade only
- implementation only
- any focused single capability already supported by the integrated upstream stack

That split keeps the system usable for both large autonomous runs and focused single-purpose work.
