---
name: implementation-execution
description: Use when the user wants supernb to implement code in an existing project or repository, including planning, coding, testing, verification, and commits, without necessarily running the full product-definition flow.
---

# Implementation Execution

This mode is for focused build work inside an existing project.

## Workflow

1. Understand the current codebase and goal.
2. If the task is ambiguous, clarify scope before coding.
3. Plan the implementation in bounded batches.
4. Code with tests and verification.
5. Commit validated work.
6. Keep the implementation artifact trail deep enough to support certification and release readiness, not just code generation.

## Hardcoded Copy Rule

- Do not write user-facing copy directly into product code.
- Externalize strings into the relevant localization layer before wiring UI.
- If the project stack has a known localization workflow, route to `i18n-localization-governance`.

## Real Feature Rule

- Do not claim a feature is implemented if it is still a placeholder, stub, TODO path, demo-only behavior, or fake backend flow.
- If the work adds or materially changes a visible user-facing feature, the batch is not complete unless the product exposes a real surfaced entry for that feature.
- If entry placement or affordance is not yet settled, stop and get an `impeccable`-backed design decision instead of hiding the feature and marking it done.

## When Not To Use It

Do not use this mode when the request is actually product discovery, competitor research, or UI/UX direction setting from scratch. Route those to the more specific modes.

## Loop Rule

For Claude Code prompt-first planning or delivery work, start with `./scripts/supernb prompt-bootstrap ... --start-loop`, then record the real Ralph Loop evidence in the final report.
If the active Claude environment does not provide the Ralph Loop stop hook, do not self-certify the batch as complete.

## Quality Bar

- Do not stop at a thin implementation that only proves a concept.
- Edge states, validation, reliability, and user-facing quality should be handled to the depth appropriate for the requested quality bar.
- Unless the user explicitly narrows scope, assume the product ambition is 10M-DAU-class and keep instrumentation, trust, and operational depth aligned with that bar.
- User-facing completion means the feature is truly landed, reachable, localized, and not dependent on hardcoded copy or placeholder UX.
