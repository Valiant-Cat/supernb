# End To End Workflow

This is the operational path for a new `supernb` initiative.

## 1. Scaffold The Initiative

```bash
make init-initiative INITIATIVE=my-product TITLE="My Product"
```

This creates a dated initiative ID and standard files across:

- `artifacts/initiatives/`
- `artifacts/research/`
- `artifacts/prd/`
- `artifacts/design/`
- `artifacts/plans/`
- `artifacts/releases/`

It also creates an `i18n-strategy.md` file in the design artifacts so localization decisions are documented before implementation.

## 2. Run Research Before PRD

Fill these first:

- `01-competitor-landscape.md`
- `02-review-insights.md`
- `03-feature-opportunities.md`

Use `sensortower-research` whenever available. Export raw data first, then summarize.

## 3. Write The PRD

Use the PRD template to convert research into:

- target users
- problem statement
- scope
- non-goals
- evidence-backed feature decisions
- evidence-backed avoidances

Do not finalize the PRD without clear citations back to the research.

## 4. Produce UI UX Direction

Use `impeccable` against the design template to define:

- brand tone
- typography
- color and contrast rules
- page structure
- interaction states
- audit notes

## 5. Write The Implementation Plan

Use the plan template with the latest `obra/superpowers` to define:

- milestones
- task batches
- dependencies
- tests-first order
- verification commands

## 6. Execute In Batches

Default path:

- use latest `superpowers`
- keep batches small
- commit validated work continuously

Optional Claude Code loop path:

- switch to the Frad plugin
- use bounded completion promises
- never run an unbounded vague loop

## 7. Final Verification

Before release:

- run final product verification
- run final `impeccable` audit for UI/UX
- confirm release checklist items
- document residual risks explicitly
