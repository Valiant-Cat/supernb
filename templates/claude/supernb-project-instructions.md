# supernb Managed Project Instructions

When the user says phrases such as:

- use supernb
- use supernb to improve this project
- 使用 supernb
- 使用 supernb 对本项目进行完善和升级
- 用 supernb 完善这个项目

treat that as an instruction to run the local `supernb` prompt-first workflow automatically.
Do not ask the user to remember the detailed command sequence.

## Default supernb prompt-first behavior

1. Run `{{SUPERNB_ROOT}}/scripts/supernb prompt-bootstrap --start-loop` before substantive work.
2. Let that command auto-discover the active initiative. If no initiative exists yet, let it initialize one for the current project first.
3. Read the generated `.supernb/initiatives/<initiative-id>/prompt-session.md`, `next-command.md`, and current phase artifacts.
4. Execute only the active phase scope unless the user explicitly asks to reopen an upstream phase.
5. If the active phase is `planning` or `delivery`, honor Ralph Loop and do not stop on self-judged completion.
6. Before claiming completion, update `prompt-report-template.json`, then run `prompt-closeout` so `.supernb` state, packets, certification, and logs stay aligned.
7. For planning and delivery, only echo the final `<promise>...</promise>` line after `prompt-closeout` succeeds.

## Skill naming rule

Use plain local skill names from `.claude/skills/`.
Do not invent namespaced local calls such as:

- `superpowers:ui-ux-upgrade`
- `superpowers:ui-ux-governance`
- `superpowers:impeccable`

For design work, use valid local skills such as:

- `ui-ux-upgrade`
- `ui-ux-governance`
- `impeccable`
- `frontend-design`
- `critique`
- `polish`
- `audit`

## User burden rule

If the user's intent is clearly "use supernb on this project", the assistant should shoulder the workflow complexity.
Do not push the full workflow back onto the user unless a concrete environment blocker prevents progress.
