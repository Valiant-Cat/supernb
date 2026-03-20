# Claude Code Ralph Loop Mode

Use this mode when you want Claude Code planning or delivery sessions to keep iterating until a real completion promise is satisfied.
For prompt-first `supernb` planning and delivery on Claude Code, this is the required enforcement layer.

## When To Use It

- you already have a written plan or current delivery batch
- the task batch is bounded
- you want the session to keep iterating until a completion promise is true

Do not use this for vague "finish the whole product" prompts. Use it for bounded planning or delivery batches.

## Install

```bash
claude plugin marketplace add FradSer/dotclaude
claude plugin install superpowers@frad-dotclaude
```

## Conflict Rule

The Frad plugin and the latest upstream plugin are both named `superpowers`.

Because they overlap in command and skill names:

- do not keep both installed side by side in one Claude Code environment
- use the latest upstream plugin as your default baseline environment
- use a separate Claude Code environment or switch the current one when you need enforced Ralph Loop behavior

## Safe Usage Pattern

Good loop tasks:

- finish task batch 2 and satisfy its acceptance criteria
- implement a specific domain model and pass its tests
- resolve a known set of review findings in a bounded file set

Bad loop tasks:

- build the entire app perfectly
- keep improving everything forever
- make the product complete with no remaining issues

## Notes

The actual loop implementation inspected in `dotclaude` is based on:

- `scripts/setup-superpower-loop.sh`
- `hooks/stop-hook.sh`

That is the mechanism `supernb` refers to when it mentions `ralph-loop`.

## How `supernb` Uses It

For Claude Code prompt-first planning and delivery:

1. Run `./scripts/supernb prompt-sync --initiative-id <initiative-id> --start-loop` inside the active Claude Code session.
2. Read `.supernb/initiatives/<initiative-id>/prompt-session.md`.
3. That command first checks that the active Claude Code environment exposes `superpowers@frad-dotclaude`, then writes `.supernb/initiatives/<initiative-id>/ralph-loop-<phase>.json`, `.supernb/initiatives/<initiative-id>/ralph-loop-<phase>-audit.json`, and `.supernb/initiatives/<initiative-id>/ralph-loop-<phase>-audit.ndjson`.
4. It then starts the Ralph Loop for the current session.
5. Work the bounded batch until the completion promise is honestly true.
6. Fill `prompt-report-template.json` with real loop evidence, then import and apply it.

Without the stop hook, the loop contract is not enforceable. In that case, do not treat the batch as cleanly complete.

For direct `./scripts/supernb execute-next --harness claude-code` runs on `planning` or `delivery`, `supernb` now auto-arms the same Ralph Loop contract, injects the bundled `dotclaude` plugin through a session-local `--plugin-dir`, binds a generated Claude session id, and writes packet-local audit files before invoking Claude Code. That direct path does not depend on the user-global plugin install in the same way prompt-first sessions do.
