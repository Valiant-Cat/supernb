---
name: single-capability-router
description: Use when the user wants a focused one-off supernb task rather than a full product workflow, and the request should be routed to the most specific capability available from superpowers, impeccable, sensortower-research, or the optional Frad loop stack.
---

# Single Capability Router

This skill is the umbrella router for one-off or narrow requests.

## Purpose

`supernb` must not reduce single-mode usage to only a few custom examples. It should expose the meaningful specialist capabilities of the integrated upstream systems.

## Routing Families

### Product Research

Route to `product-research-prd` or the relevant `sensortower-research` pull when the user asks for:

- competitor analysis
- app metadata lookup
- downloads or revenue estimates
- rankings
- keyword research
- review mining
- rating history
- creatives analysis

### Product Definition And Ideation

Route to `brainstorm-and-save` or upstream `superpowers` brainstorming or planning flows when the user asks for:

- brainstorming
- feature shaping
- option analysis
- implementation planning
- saved strategy notes

### Design And UX

Route to `ui-ux-governance`, `ui-ux-upgrade`, or the relevant `impeccable` capability family when the user asks for:

- frontend design
- audit
- critique
- polish
- normalize
- typeset
- arrange
- animate
- responsive adaptation
- copy clarity
- onboarding design
- visual boldening or quieting

### Engineering Execution

Route to `implementation-execution`, `autonomous-delivery`, or upstream `superpowers` engineering flows when the user asks for:

- test-driven implementation
- debugging
- code review
- plan execution
- branch finishing
- worktree-based isolation
- parallel agent execution
- verification before completion

### Localization And Translation

Route to `i18n-localization-governance` when the user asks for:

- extracting hardcoded strings
- localization setup
- translation completion
- multi-language support
- ARB sync
- Android strings.xml localization
- keeping copy out of source code

### Loop Persistence

Route to the optional Frad loop flow only when:

- the environment intentionally uses that plugin
- the task is bounded
- honest completion can be verified

## Anti-Reduction Rule

Do not answer "supernb only supports A, B, C" when the integrated upstream stack supports more specialist modes. Route to the narrowest correct capability.
