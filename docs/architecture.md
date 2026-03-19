# supernb Architecture

## Core Idea

`supernb` is a phase-gated orchestration system for full-product delivery. It coordinates research, PRD generation, design, implementation, and verification. Each phase has a designated upstream engine and a required artifact set. The default ambition is not a thin commercial MVP; it is a product direction that can plausibly support a 10M-DAU-grade bar.

The `supernb` artifact templates are optional scaffolding. They provide a stable place to save outputs, but they do not override the native plan, design, or execution documentation formats that upstream `superpowers` may generate when a richer structure is warranted.

`supernb` now also uses an initiative control file at `.supernb/initiatives/<initiative-id>/initiative.yaml` inside the active product workspace. That file is the machine-readable source of truth for phase routing, gate evaluation, and next-command generation.

Phase gate truth is split across two layers:

- phase artifacts still carry human-readable status fields
- initiative-local certification state records whether a phase actually passed structural and semantic certification

Completion should require both, not just a flipped markdown field.

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
- scale signals and market headroom
- global and regional usage or complaint patterns

Storage target:

- `.supernb/research/`
- `.supernb/initiatives/`

Gate:

- no PRD may be finalized without citing the research window, countries, and apps reviewed

### 2. PRD

Primary engine: `supernb` orchestration + `superpowers` brainstorming discipline

Required outputs:

- product brief
- user problems and target segments
- scope and non-goals
- core journeys
- growth system
- success metrics
- scale-readiness and trust requirements
- evidence appendix linking back to research

Storage target:

- `.supernb/prd/`
- `.supernb/initiatives/`

Gate:

- PRD must explicitly tie feature choices to competitor evidence or review evidence

### 3. UI/UX Design

Primary engine: `impeccable`

Required outputs:

- visual direction
- typography and color rules
- page-by-page UI/UX notes
- design-system definition
- key journey surface deep dives
- interaction and empty-state behavior
- accessibility and contrast review
- interaction polish, trust, and recovery cues
- scale UX requirements for onboarding, repeat use, power users, and global adaptation
- explicit `impeccable` workflow evidence across foundation, critique, and polish passes

Storage target:

- `.supernb/design/`
- `.supernb/initiatives/`

Gate:

- no implementation starts before the design pass calls out contrast, readability, state coverage, key journey depth, and final impeccable audit notes

### 4. Planning And Delivery

Primary engine: latest `obra/superpowers`

Required outputs:

- implementation plan
- task dependency graph
- test-first execution order
- validation checkpoints
- scale and reliability workstreams

Storage target:

- `.supernb/plans/`
- `.supernb/initiatives/`

Gate:

- tasks must be granular enough for autonomous execution and review

### 5. Autonomous Execution Loop

Primary engine: latest `superpowers` plus Ralph Loop enforcement when Claude Code runs prompt-first planning or delivery

Loop model:

- create or update the state file with `setup-superpower-loop.sh`
- run bounded batches with explicit completion promises
- use BDD/TDD to keep Red and Green phases verifiable
- commit each validated batch

Gate:

- completion requires passing verification, not just code generation
- Claude Code prompt-first planning and delivery must not stop on self-judgment alone

### 6. Release Readiness

Primary engines: `superpowers` verification and `impeccable` final UX audit

Required outputs:

- final design audit
- final test results
- release notes
- git tag or release commit trail
- rollout or rollback controls
- post-launch watchlist

Storage target:

- `.supernb/releases/`
- `.supernb/initiatives/`

## Coordination Rules

1. Research is mandatory before PRD.
2. PRD is mandatory before design finalization.
3. Design approval is mandatory before implementation.
4. `impeccable` is used both before and after frontend implementation.
5. Latest `superpowers` is the default execution baseline.
6. Claude Code prompt-first planning and delivery use Ralph Loop as the anti-self-termination layer.
7. Do not install two same-named `superpowers` plugins in one Claude Code environment.
8. Every verified batch is committed to git.
9. Hardcoded-copy checks should run before release when UI code is in scope.
10. Phase advancement requires both artifact status updates and passing certification evidence.

## Cross-Cutting Localization Rule

- User-facing copy must not be hardcoded in product code, whether the target is app, web, or another UI surface.
- New strings should be added to the relevant localization resources first, then referenced from code.
- If a framework-specific localization workflow exists, `supernb` should route to it instead of inventing inline copy patterns.
- Translation coverage and extraction of hardcoded strings are part of release readiness, not optional cleanup.

## Why This Split Works

- `sensortower-research` provides evidence
- `superpowers` provides execution discipline
- `ralph-loop` provides enforced persistence for Claude Code prompt-first planning and delivery
- `impeccable` provides design quality control

Each tool covers a real weakness of the others instead of duplicating them.
