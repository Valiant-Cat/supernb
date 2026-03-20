---
name: ui-ux-upgrade
description: Use when the user wants supernb to upgrade the UI and UX of an existing local project, including visual direction, implementation changes, and post-change design auditing.
---

# UI UX Upgrade

This mode is for existing codebases, not greenfield ideation.

## Required Workflow

1. Inspect the current project and current UX issues.
2. Capture design context or ask for it if missing.
3. Use the local `impeccable` router or the concrete impeccable skills `teach-impeccable` and `frontend-design` to define the upgrade direction and design-system delta.
4. Use `critique` to inspect the highest-value flows, states, trust cues, and conversion or retention surfaces.
5. Implement the UI/UX changes in code.
6. Run `polish`, then a post-implementation `audit`.
7. Record the upgrade notes locally.

Never invent namespaced calls like `superpowers:ui-ux-upgrade`. The valid local skill name is `ui-ux-upgrade`.

## Minimum Deliverables

- design direction
- design-system delta
- key surface or journey upgrade plan
- implemented changes
- final audit notes

## Anti-Pattern Rule

Do not stop at a critique. This mode is expected to carry through implementation unless the user explicitly asks for review only.
