# End To End Workflow

This is the operational path for a new `supernb` initiative.

## 1. Scaffold The Initiative

```bash
./scripts/supernb init-initiative my-product "My Product"
```

This creates a dated initiative ID and standard files inside the active product workspace under `.supernb/`:

- `.supernb/initiatives/`
- `.supernb/research/`
- `.supernb/prd/`
- `.supernb/design/`
- `.supernb/plans/`
- `.supernb/releases/`

It also creates:

- `.supernb/initiatives/<initiative-id>/initiative.yaml`
- `.supernb/initiatives/<initiative-id>/run-status.md`
- `.supernb/initiatives/<initiative-id>/run-status.json`
- `.supernb/initiatives/<initiative-id>/certification-state.json`
- `.supernb/initiatives/<initiative-id>/next-command.md`
- `.supernb/initiatives/<initiative-id>/executions/`

And it creates an `i18n-strategy.md` file in the design artifacts so localization decisions are documented before implementation.

## 2. Fill The Initiative Spec

Update `initiative.yaml` before execution starts.

At minimum, fill:

- `delivery.goal`
- `delivery.product_category`
- `delivery.markets`
- `delivery.research_window`

Before planning and delivery, also fill:

- `delivery.repository`
- `delivery.platform`
- `delivery.stack`
- `delivery.scale_target_dau`
- `delivery.quality_bar`

## 3. Run The Phase Controller

```bash
./scripts/supernb run --initiative-id <initiative-id>
```

This computes the first incomplete phase, writes `run-status.md`, and generates `next-command.md` when the phase is ready.
It also archives a timestamped phase brief, writes `phase-packet.md`, and appends to `run-log.md`.

Then execute the current phase through a supported harness:

```bash
./scripts/supernb execute-next \
  --initiative-id <initiative-id> \
  --harness codex \
  --project-dir /path/to/repo
```

Then apply the generated execution packet:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet \
  --certify
```

After the phase work is done, record it:

```bash
./scripts/supernb record-result \
  --initiative-id <initiative-id> \
  --status succeeded \
  --summary "Describe the completed batch"
```

Before advancing, certify the artifact set against both structural and semantic readiness:

```bash
./scripts/supernb certify-phase \
  --initiative-id <initiative-id> \
  --phase research
```

If that work should advance the gate, apply the status update:

```bash
./scripts/supernb advance-phase \
  --initiative-id <initiative-id> \
  --phase research \
  --status approved \
  --actor supernb
```

## 4. Run Research Before PRD

Fill these first:

- `01-competitor-landscape.md`
- `02-review-insights.md`
- `03-feature-opportunities.md`

Use `sensortower-research` whenever available. Export raw data first, then summarize.

## 5. Write The PRD

Use the PRD template to convert research into:

- target users
- problem statement
- scope
- non-goals
- evidence-backed feature decisions
- evidence-backed avoidances

Do not finalize the PRD without clear citations back to the research.

## 6. Produce UI UX Direction

Use `impeccable` against the design template to define:

- brand tone
- typography
- color and contrast rules
- page structure
- interaction states
- audit notes

## 7. Write The Implementation Plan

Use the plan template with the latest `obra/superpowers` to define:

- milestones
- task batches
- dependencies
- tests-first order
- verification commands

## 8. Execute In Batches

Default path:

- use latest `superpowers`
- keep batches extremely small and explicit
- treat each delivery run as one validated batch
- commit validated work continuously instead of waiting for a final all-at-once push
- record whether brainstorming, writing-plans, TDD, and code review were used in the execution packet

Optional Claude Code loop path:

- switch to the Frad plugin
- use bounded completion promises
- never run an unbounded vague loop

## 9. Final Verification

Before release:

- run final product verification
- run final `impeccable` audit for UI/UX
- confirm release checklist items
- document residual risks explicitly

After each phase approval, rerun:

```bash
./scripts/supernb run --initiative-id <initiative-id>
```
