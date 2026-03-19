# Claude Code Loop Mode

Use this mode only when you explicitly want the FradSer Superpower Loop on Claude Code.

## When To Use It

- you already have a written plan
- the task batch is bounded
- you want the session to keep iterating until a completion promise is true

Do not use this as your default `supernb` baseline.

## Install

```bash
claude plugin marketplace add FradSer/dotclaude
claude plugin install superpowers@frad-dotclaude
```

## Conflict Rule

The Frad plugin and the latest upstream plugin are both named `superpowers`.

Because they overlap in command and skill names:

- do not keep both installed side by side in one Claude Code environment
- use the latest upstream plugin as your default
- switch to the Frad plugin only for sessions that need loop behavior

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
