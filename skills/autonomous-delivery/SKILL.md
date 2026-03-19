---
name: autonomous-delivery
description: Use when PRD and design are already approved and the next step is autonomous implementation, test-first execution, iterative fixing, and continuous commits using the latest superpowers baseline, with the FradSer loop workflow only as an optional bounded enhancer.
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
3. Execute in small batches with tests first.
4. When a task benefits from persistence and you are in a Claude Code environment that intentionally uses the Frad plugin, run the FradSer Superpower Loop with:
   - an explicit state file
   - a bounded completion promise
   - a realistic max iteration cap
5. Review the output before marking complete.
6. Commit each validated batch.

## Loop Safety

Never use an unbounded loop for vague objectives like "build the whole app perfectly".

Do not assume the loop is always available. The default `supernb` baseline is the latest upstream `superpowers`, not the Frad plugin.

Good loop tasks:

- implement the domain model and pass its tests
- complete task batch 3 and satisfy its exit criteria
- fix failing review findings in a known file set

## Completion Rule

Code generation is not completion. Completion requires verification evidence.

## Template Rule

If an initiative scaffold exists, record plan progress and release readiness in the corresponding plan and release artifacts.
