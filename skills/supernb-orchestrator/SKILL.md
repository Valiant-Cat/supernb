---
name: supernb-orchestrator
description: Use when the goal is full product delivery from idea to commercial-grade release, and the work must coordinate research, PRD, UI/UX design, implementation, verification, and git commits.
---

# supernb Orchestrator

This skill coordinates the end-to-end `supernb` workflow. It is the top-level router, not the deep expert for each phase.

## Mandatory Phase Order

1. Research
2. PRD
3. UI/UX design
4. implementation planning
5. autonomous execution
6. final verification and release readiness

Never skip straight to coding when the product direction is still unclear.

## Routing Rules

- For competitor analysis, app reviews, market signals, or feature opportunity discovery, use `product-research-prd`.
- For UI/UX generation or review, use `ui-ux-governance`.
- For implementation after PRD and design approval, use `autonomous-delivery`.
- If upstream `superpowers` skills are available, use them for brainstorming, planning, and execution instead of improvising ad hoc workflows.

## Deliverable Rules

Before implementation begins, the workspace should contain:

- a research artifact set
- a PRD
- a design artifact set
- an execution plan

Before release, the workspace should contain:

- verification evidence
- final design audit notes
- a clean commit trail

## Commit Rule

Each validated batch should end in a git commit. Avoid giant unreviewable changesets.

