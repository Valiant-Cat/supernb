---
name: ui-ux-governance
description: Use when creating, refining, reviewing, or validating UI/UX for a product, especially when typography, color, layout, interaction clarity, contrast, and page-level quality need to be enforced consistently.
---

# UI UX Governance

This skill ensures the integrated impeccable skill family is used as a design and review layer, not just as a one-shot styling prompt.

## Mandatory Context

Before design work starts, confirm:

- target audience
- use cases
- brand tone

If design context is missing, gather it first.

## Mandatory Use Of Impeccable

Use plain local skill names. Do not invent namespaced local calls such as `superpowers:ui-ux-governance` or `superpowers:impeccable`.

Use the local `impeccable` router or concrete skills from that family:

- before page design, use `teach-impeccable` or `frontend-design` to establish visual direction and design-system principles
- during page design, use `critique` to inspect hierarchy, interaction quality, retention surfaces, and trust cues
- after implementation, use `polish` and then `audit` to review contrast, readability, spacing, responsive behavior, interaction polish, and localization layout resilience

At minimum, run the impeccable family as three passes:

- foundation pass: direction, tone, hierarchy, type, color, spacing
- critique pass: flows, states, friction, trust, conversion, retention, anti-patterns
- polish pass: motion, responsiveness, perceived quality, recovery cues, localization stress points

## Minimum Quality Checks

- buttons must remain readable against their background
- text contrast must be intentional and legible
- empty, loading, error, and success states must be designed
- page hierarchy must be obvious without relying on generic cards everywhere
- mobile layouts must adapt, not just shrink
- key user flows must be covered, not just isolated screens
- trust, guidance, and recovery cues must be designed deliberately
- the output should feel like a product system, not a style pass on a demo layout
- onboarding, repeat-use surfaces, localization adaptation, and support paths should feel credible for a 10M-DAU-class product
- conversion, retention, and monetization surfaces must be deliberate, not bolted on
- key surfaces should be deep enough to guide implementation without guesswork
- the design system should define reusable patterns instead of page-by-page improvisation

## Release Rule

Frontend work is not complete until a final `impeccable` review pass is done after code implementation.

## Template Rule

If an initiative scaffold exists, prefer saving UI/UX decisions and audits into the corresponding design artifacts.

The saved artifact should be rich enough to preserve:

- product experience strategy
- design-system definition
- key journey surface deep dives
- interaction and motion details
- impeccable workflow evidence
- explicit design debt and open tradeoffs

Do not reduce the depth of `impeccable` or upstream design outputs merely to fit a smaller local template. Preserve full detail when it adds value.
