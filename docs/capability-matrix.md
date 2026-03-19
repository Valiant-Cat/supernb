# Capability Matrix

This file defines what `supernb` should treat as supported single-capability modes.

`supernb` is not limited to a short custom list. It should expose the relevant specialist abilities already present in the integrated upstream stack.

## 1. `obra/superpowers`

Observed specialist skills:

- `brainstorming`
- `writing-plans`
- `executing-plans`
- `dispatching-parallel-agents`
- `subagent-driven-development`
- `test-driven-development`
- `systematic-debugging`
- `requesting-code-review`
- `receiving-code-review`
- `verification-before-completion`
- `using-git-worktrees`
- `finishing-a-development-branch`
- `writing-skills`

`supernb` expectation:

- any user request matching these specialist engineering workflows should be routed to them, not flattened into one generic implementation mode

## 2. `impeccable`

Observed specialist design skills:

- `frontend-design`
- `audit`
- `critique`
- `normalize`
- `polish`
- `distill`
- `clarify`
- `optimize`
- `harden`
- `animate`
- `colorize`
- `bolder`
- `quieter`
- `delight`
- `extract`
- `adapt`
- `onboard`
- `typeset`
- `arrange`
- `overdrive`
- `teach-impeccable`

`supernb` expectation:

- any design-specific request should route to the narrowest matching design capability instead of a single blanket UI mode

## 3. `sensortower-research`

Observed specialist research commands:

- `search`
- `metadata`
- `sales`
- `rankings`
- `top-apps`
- `keywords`
- `keyword-research`
- `reviews`
- `review-summary`
- `ratings`
- `creatives`
- `review-insights`
- `raw`
- `docs`

`supernb` expectation:

- any app intelligence request should route to the specific dataset pull the user actually needs

## 4. Local Translation Skills

Observed localization workflows:

- `flutter-l10n-translation`
- `android-i18n-translation`

`supernb` expectation:

- user-facing strings must be extracted into localization resources rather than hardcoded in code
- Flutter projects should route to the ARB workflow when localization or translation is needed
- Android projects should route to the strings.xml extraction and translation workflow when localization or translation is needed
- the same externalization principle should be enforced for web and other stacks, even if a different concrete i18n toolchain is used

## 5. `dotclaude` Superpower Loop Layer

Observed specialist additions:

- `behavior-driven-development`
- `agent-team-driven-development`
- loop setup script
- stop hook persistence behavior

`supernb` expectation:

- these are optional specialist execution enhancers, not the default baseline
- route to them only when the environment intentionally supports them and the task is bounded enough to verify honestly

## Routing Principle

When a user asks for one focused thing, `supernb` should answer with the narrowest correct capability from the matrix above.

When a user asks for a whole product, `supernb` should orchestrate multiple capabilities across the matrix.
