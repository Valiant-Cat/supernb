---
name: supernb
description: Use when the user says to use supernb, refine a project with supernb, or wants the full supernb product workflow by prompt instead of manually running terminal commands.
---

# supernb Prompt-First Entry

This is the prompt-first entrypoint for `supernb`.

If the user says things like:

- use supernb
- 用 supernb 做
- 使用 supernb 完善这个项目
- use supernb to improve this app

do not only imitate the methodology. Treat that as a request to run the `supernb` control plane under the hood.

## Mandatory Prompt-First Workflow

1. Resolve the active initiative first.
2. In Claude Code, run `prompt-sync --start-loop` before doing substantive work.
3. Read the generated `prompt-session.md`, `next-command.md`, and current phase artifacts.
4. Execute only the current phase scope unless the user explicitly asks to re-open an upstream phase.
5. Before finishing, write a structured execution report and import or apply it so the initiative state, packets, and certification records stay aligned.

For Claude Code planning and delivery phases, `prompt-sync --start-loop` both generates the Ralph Loop contract and starts it in the current session. Do not let the agent stop on self-judged completion. Only allow exit when the completion promise is honestly true.

## Required Commands The Agent Should Run Internally

From the managed `supernb` repo or install root:

```bash
./scripts/supernb prompt-sync --initiative-id <initiative-id> --start-loop
```

If the initiative id is unknown but the current repo already has one initiative:

```bash
./scripts/supernb prompt-sync --start-loop
```

That command refreshes `run-status.json`, writes `prompt-session.md`, and creates a `prompt-report-template.json` for this session.
For Claude Code planning and delivery phases it also writes `ralph-loop-<phase>.md` and `ralph-loop-<phase>.json`, then starts the Ralph Loop in the current Claude session.

## Closeout Rule

Prompt-first supernb work is not complete when only code changed.

The agent must also:

1. Fill `prompt-report-template.json` with real summary, commands, tests, evidence artifacts, workflow trace, validated batch count, and commit IDs.
2. Import it:

```bash
./scripts/supernb import-execution --spec <initiative.yaml> --phase <active-phase> --report-json <prompt-report-template.json> --harness claude-code-prompt
```

3. Apply it:

```bash
./scripts/supernb apply-execution --spec <initiative.yaml> --packet <latest-imported-packet> --certify
```

If the batch is truly phase-complete and clean, `--apply-certification` is allowed instead of `--certify`.

If the prompt session marked Ralph Loop as required, the final response must also include the exact loop completion promise and the imported report must record real loop evidence.

## Routing Rule

After `prompt-sync`, route to the correct deeper skill:

- full product flow: `supernb-orchestrator` or `full-product-delivery`
- research and PRD: `product-research-prd`
- UI and UX: `ui-ux-governance`
- coding in an existing codebase: `implementation-execution` or `autonomous-delivery`

But keep the initiative control plane synchronized before and after the deeper work.
