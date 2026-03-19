---
name: autonomous-delivery
description: Use when PRD and design are already approved and the next step is autonomous implementation, test-first execution, iterative fixing, and continuous commits using the latest superpowers baseline, while enforcing Ralph Loop for Claude Code prompt-first planning or delivery sessions.
---

# Autonomous Delivery

This skill governs the build stage.

## Preconditions

Do not start if these are missing:

- approved PRD
- approved UI/UX design
- implementation scope

## Required Workflow

1. Use upstream `superpowers` to refine brainstorming if needed.
2. Use upstream `superpowers` writing-plans or equivalent planning flow.
3. In Claude Code prompt-first sessions, run `./scripts/supernb prompt-sync ... --start-loop` before substantive batch execution.
4. Execute in small batches with tests first.
5. For Claude Code prompt-first planning or delivery sessions, make sure the Ralph Loop has been started before substantive execution with:
   - an explicit state file
   - a bounded completion promise
   - a realistic max iteration cap
   - a stop-hook-enabled Claude Code environment
6. If the stop hook is unavailable, do not claim clean completion. End the batch as `needs-follow-up` and switch to a loop-enabled Claude environment.
7. Review the output before marking complete.
8. Commit each validated batch.
9. Treat each execution run as one validated batch unless the user explicitly scopes a larger bounded batch.
10. Record in the execution packet whether brainstorming, writing-plans, TDD, code review, and Ralph Loop were used in this run.
11. Keep the delivery artifact trail rich enough for release readiness:
   - update implementation plan progress
   - update release-readiness inputs when relevant
   - keep evidence at commercial-product depth rather than demo depth
   - preserve the implementation depth needed for a 10M-DAU-class product, including observability, trust, and growth instrumentation when relevant

## Loop Safety

Never use an unbounded loop for vague objectives like "build the whole app perfectly".

Do not use Ralph Loop as an excuse for vague goals. The batch still has to be bounded enough to verify honestly.
If Claude Code prompt-first planning or delivery is the active mode, Ralph Loop is part of the completion contract, not an optional extra.

Good loop tasks:

- implement the domain model and pass its tests
- complete task batch 3 and satisfy its exit criteria
- fix failing review findings in a known file set

## Completion Rule

Code generation is not completion. Completion requires verification evidence.
Shallow feature coverage is not completion either. Delivery should move the product meaningfully toward the approved journeys and capability set.

## Template Rule

If an initiative scaffold exists, record plan progress and release readiness in the corresponding plan and release artifacts.
The initiative scaffold should live in the product project's `.supernb/` directory by default.

But do not replace upstream `superpowers` planning or execution documents with a thinner local version. Use the local scaffold as an index or landing zone, not as a restriction on capability.
