---
name: supernb-orchestrator
description: Use when the goal is either full product delivery from idea to commercial-grade release or correct routing to any single capability exposed by the integrated upstream systems, without assuming a fixed framework or stack.
---

# supernb Orchestrator

This skill coordinates the end-to-end `supernb` workflow. It is the top-level router, not the deep expert for each phase.

`supernb` is framework-agnostic. Flutter, React Native, native Android, iOS, web, backend, Python, Go, or other stacks are request parameters, not routing determinants by themselves.

`supernb` templates are optional storage scaffolds. Do not force upstream `superpowers` into a weaker or smaller document structure just because a local template exists.

## Mandatory Phase Order

1. Research
2. PRD
3. UI/UX design
4. implementation planning
5. autonomous execution
6. final verification and release readiness

Never skip straight to coding when the product direction is still unclear.

## Routing Rules

- For a request to build a complete product from idea to shippable commercial-grade release, use `full-product-delivery`.
- For a request to use any one specific upstream capability without running the full product flow, use `single-capability-router`.
- For brainstorming with local document output, use `brainstorm-and-save`.
- For competitor analysis, app reviews, market signals, or feature opportunity discovery, use `product-research-prd`.
- For UI/UX generation or review, use `ui-ux-governance`.
- For UI/UX modernization of an existing local project, use `ui-ux-upgrade`.
- For implementation after PRD and design approval, use `autonomous-delivery`.
- For focused coding or feature implementation in an existing codebase, use `implementation-execution`.
- If upstream `superpowers` skills are available, use them for brainstorming, planning, execution, review, debugging, worktrees, and related specialist flows instead of improvising ad hoc workflows.
- If upstream `impeccable` commands are available, route design-specific requests to the relevant command family instead of collapsing everything into one generic design pass.
- If local `sensortower-research` is available, route research-specific requests to the correct dataset pull instead of producing hand-wavy summaries.

## Coverage Rule

`supernb` should support:

- full-product orchestration
- all relevant single-capability flows from the integrated upstreams

Do not artificially limit single-mode support to a small handpicked subset if the upstream systems expose more specific capabilities.

## Deliverable Rules

Before implementation begins, the workspace should contain:

- a research artifact set
- a PRD
- a design artifact set
- an execution plan

Those artifacts should be stored in the active product project's `.supernb/` workspace by default.

Before release, the workspace should contain:

- verification evidence
- final design audit notes
- a clean commit trail

These outputs may be stored in `supernb` artifacts, in richer upstream-generated documents, or both. Prefer preserving upstream detail rather than flattening it into a smaller local template.

## Commit Rule

Each validated batch should end in a git commit. Avoid giant unreviewable changesets.
