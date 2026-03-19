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

If the work was run manually, or via OpenCode after preparing the prompt, import a structured execution report first:

```bash
./scripts/supernb import-execution \
  --initiative-id <initiative-id> \
  --phase <phase> \
  --report-json /path/to/report.json
```

That import will now fail immediately if the declared evidence artifact paths do not exist.

After the phase work is done, record it:

```bash
./scripts/supernb record-result \
  --initiative-id <initiative-id> \
  --status needs-follow-up \
  --summary "Describe the completed batch" \
  --source manual-override \
  --override-reason "Packet evidence was incomplete"
```

Use this path only for controlled overrides. Packet-backed execution results should keep flowing through `apply-execution`.

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

For a legacy loose `.supernb` workspace that predates initiatives, create the new initiative and then run:

```bash
./scripts/supernb migrate-legacy --initiative-id <initiative-id>
```

That flow now writes both `legacy-import.md` and `legacy-mapping.md/json` so the imported files come with suggested target artifacts.

If repeated previews and retries have filled `executions/` with stale packets, preview cleanup candidates with:

```bash
./scripts/supernb clean-initiative --initiative-id <initiative-id>
```

Re-run with `--apply` to archive the selected artifacts into a cleanup session and manifest, or add `--delete` for an explicit hard-delete.

## 4. Run Research Before PRD

Fill these first:

- `01-competitor-landscape.md`
- `02-review-insights.md`
- `03-feature-opportunities.md`

Use `sensortower-research` whenever available. Export raw data first, then summarize.
Carry the core insights forward into the PRD traceability matrix with stable `Trace ID` rows so later design, planning, and release docs can prove they are still building the same product row by row.

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
- design-system rules
- key journey surface deep dives
- conversion and retention surfaces
- audit notes from foundation, critique, and polish passes

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

Claude Code prompt-first planning or delivery path:

- switch to a Ralph Loop-enabled Claude Code environment
- use bounded completion promises
- start the generated `ralph-loop-<phase>` contract before substantive work
- never run an unbounded vague loop

## 9. Final Verification

Before release:

- run final product verification
- run final `impeccable` audit for UI/UX
- confirm interaction polish, trust cues, and localization layout quality
- confirm release checklist items
- document residual risks explicitly

After each phase approval, rerun:

```bash
./scripts/supernb run --initiative-id <initiative-id>
```
