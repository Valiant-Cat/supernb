---
name: full-product-delivery
description: Use when the user wants supernb to take a product from idea to a 10M-DAU-grade commercial release-ready implementation, including research, PRD, UI/UX, coding, verification, and continuous commits rather than a thin MVP, regardless of framework or stack.
---

# Full Product Delivery

This is the highest-autonomy `supernb` mode.

## What It Means

The target is not a demo or placeholder implementation. The target is a release-ready product direction with:

- research-backed scope
- documented PRD
- deliberate UI/UX
- implementation plans
- iterative code delivery
- verification evidence
- commit history

Every phase artifact should be rich enough to support real product decisions. Do not collapse research, PRD, design, or release documentation into thin demo-level summaries.
Default to a product ambition that could plausibly support at least 10 million daily active users unless the user explicitly narrows the ambition.

## Required Inputs

- product idea
- target platform and stack
- remote repository location if code must be pushed
- quality bar or product constraints

## Execution Rules

1. Create or identify the initiative artifact set first.
   Save it in the product project's `.supernb/` workspace by default, not only inside the supernb repo.
2. Run research before locking the PRD.
3. Run design before major frontend implementation.
4. Use latest `superpowers` as the default implementation engine.
5. Use the Frad loop only as an optional bounded persistence layer.
6. Keep shipping in validated batches with commits.
7. Push `superpowers` to decompose work as finely as possible instead of hiding large unreviewed batches behind one final response.
8. Carry depth through all phases:
   - research should be globally and regionally informed
   - PRD should define a product system, not a short feature list
   - design should cover flows, states, trust, and responsive behavior
   - implementation and release artifacts should be concrete enough to certify

## Localization Rule

- Do not hardcode user-facing copy in code.
- Treat localization resources as the source of truth for app and web copy.
- If the environment provides a framework-specific translation workflow, use it.
- Multi-language support requirements should be captured in PRD, design, implementation plan, and release checks.

## Scope Discipline

The user may ask for "one shot" delivery, but the work must still proceed through gated phases. Do not skip evidence, design, testing, or verification in the name of speed.

## Mobile And Globalization Rule

If the request includes mobile apps, internationalization, or broad language support, capture that in the PRD and design artifacts early instead of bolting it on later.

## Framework Neutrality

Flutter is one possible stack, not a default. The same mode applies to web apps, backend systems, native mobile apps, cross-platform apps, desktop tools, or mixed-stack products.
