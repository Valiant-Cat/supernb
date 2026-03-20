---
name: impeccable
description: Use when the user asks to use impeccable for UI/UX direction, critique, polish, audit, or broader design-system refinement and you need a valid entry skill instead of inventing a missing generic skill name.
---

# impeccable Router

`impeccable` in this workspace is not one monolithic skill with every behavior inside it.
It is a capability family exposed through concrete first-level skills such as:

- `teach-impeccable`
- `frontend-design`
- `critique`
- `polish`
- `audit`
- `adapt`
- `typeset`
- `colorize`
- `arrange`
- `animate`

## Naming Rule

Use plain first-level local skill names.

Do not invent namespaced local skill calls like:

- `superpowers:ui-ux-upgrade`
- `superpowers:ui-ux-governance`
- `superpowers:impeccable`

For local `supernb` and `impeccable` skills, the valid names are the directory names visible under `.claude/skills/`.

## Default Routing

When the user says "use impeccable" without more detail:

1. If project design context is weak or missing, start with `teach-impeccable`.
2. For foundational UI direction or system-level design structure, use `frontend-design`.
3. For design criticism or identifying UX problems, use `critique`.
4. For implementation refinement and perceived quality improvements, use `polish`.
5. For final post-implementation review, use `audit`.

## supernb Integration

When this is invoked inside a `supernb` phase:

- keep the active initiative artifacts aligned
- save findings into the corresponding design or release artifacts
- do not stop at "impeccable critique" if the surrounding `supernb` mode requires implementation and closeout

## Anti-Pattern Rule

Do not fail over to a made-up skill name when a concrete impeccable family skill already exists.
Route to the narrowest real skill that matches the requested design task.
