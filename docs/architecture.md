# supernb Architecture

## Core Idea

`supernb` is a phase-gated orchestration system for full-product delivery. It coordinates research, PRD generation, design, implementation, and verification. Each phase has a designated upstream engine and a required artifact set.

## Phases

### 1. Research

Primary engine: local `sensortower-research`

Required outputs:

- competitor shortlist
- metadata snapshot
- review export
- review insight summary
- feature opportunity list
- anti-feature list

Storage target:

- `artifacts/research/`
- `artifacts/initiatives/`

Gate:

- no PRD may be finalized without citing the research window, countries, and apps reviewed

### 2. PRD

Primary engine: `supernb` orchestration + `superpowers` brainstorming discipline

Required outputs:

- product brief
- user problems and target segments
- scope and non-goals
- core journeys
- success metrics
- evidence appendix linking back to research

Storage target:

- `artifacts/prd/`
- `artifacts/initiatives/`

Gate:

- PRD must explicitly tie feature choices to competitor evidence or review evidence

### 3. UI/UX Design

Primary engine: `impeccable`

Required outputs:

- visual direction
- typography and color rules
- page-by-page UI/UX notes
- interaction and empty-state behavior
- accessibility and contrast review

Storage target:

- `artifacts/design/`
- `artifacts/initiatives/`

Gate:

- no implementation starts before the design pass calls out contrast, readability, and state coverage

### 4. Planning And Delivery

Primary engine: latest `obra/superpowers`

Required outputs:

- implementation plan
- task dependency graph
- test-first execution order
- validation checkpoints

Storage target:

- `artifacts/plans/`
- `artifacts/initiatives/`

Gate:

- tasks must be granular enough for autonomous execution and review

### 5. Autonomous Execution Loop

Primary engine: optional `superpowers@frad-dotclaude`

Loop model:

- create or update the state file with `setup-superpower-loop.sh`
- run bounded batches with explicit completion promises
- use BDD/TDD to keep Red and Green phases verifiable
- commit each validated batch

Gate:

- completion requires passing verification, not just code generation
- this layer is optional and should not replace the primary `superpowers` baseline

### 6. Release Readiness

Primary engines: `superpowers` verification and `impeccable` final UX audit

Required outputs:

- final design audit
- final test results
- release notes
- git tag or release commit trail

Storage target:

- `artifacts/releases/`
- `artifacts/initiatives/`

## Coordination Rules

1. Research is mandatory before PRD.
2. PRD is mandatory before design finalization.
3. Design approval is mandatory before implementation.
4. `impeccable` is used both before and after frontend implementation.
5. Latest `superpowers` is the default execution baseline.
6. The Frad loop is only used as an optional bounded persistence layer on Claude Code.
7. Do not install two same-named `superpowers` plugins in one Claude Code environment.
8. Every verified batch is committed to git.
9. Hardcoded-copy checks should run before release when UI code is in scope.

## Cross-Cutting Localization Rule

- User-facing copy must not be hardcoded in product code, whether the target is app, web, or another UI surface.
- New strings should be added to the relevant localization resources first, then referenced from code.
- If a framework-specific localization workflow exists, `supernb` should route to it instead of inventing inline copy patterns.
- Translation coverage and extraction of hardcoded strings are part of release readiness, not optional cleanup.

## Why This Split Works

- `sensortower-research` provides evidence
- `superpowers` provides execution discipline
- `ralph-loop` provides optional persistence
- `impeccable` provides design quality control

Each tool covers a real weakness of the others instead of duplicating them.
