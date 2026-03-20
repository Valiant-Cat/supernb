# supernb Managed User Instructions

When the user says phrases such as:

- use supernb
- use supernb to improve this project
- 使用 supernb
- 使用 supernb 对本项目进行完善和升级
- 用 supernb 完善这个项目

treat that as a request to run the `supernb` prompt-first workflow automatically in the current workspace.
Do not ask the user to remember the detailed command sequence.

## Default supernb prompt-first behavior

1. Run `{{SUPERNB_ROOT}}/scripts/supernb prompt-bootstrap --start-loop --direct-bridge-fallback` from the current project workspace before substantive work.
2. Let that command auto-discover the active initiative. If no initiative exists yet, let it initialize one for the current project first.
3. Read the generated `.supernb/initiatives/<initiative-id>/prompt-session.md`, `next-command.md`, `initiative-reassessment.md`, and current phase artifacts.
4. Start with an initiative-wide reassessment. Compare the real repository state against research, PRD, design, planning, delivery, and release artifacts before deciding the work is only a current-phase patch.
5. If the reassessment finds stale upstream artifacts, reopen the earliest affected phase instead of only editing the current active phase.
6. If the active phase is `planning` or `delivery`, honor Ralph Loop and do not stop on self-judged completion.
7. Before claiming completion, update `prompt-report-template.json`, then run `prompt-closeout` so `.supernb` state, packets, certification, and logs stay aligned.
8. For planning and delivery, only echo the final `<promise>...</promise>` line after `prompt-closeout` succeeds.

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
