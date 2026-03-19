# Initiative Spec

`supernb` now uses a per-initiative control file:

- `artifacts/initiatives/<initiative-id>/initiative.yaml`

This file is the single source of truth for the runner.

## Why It Exists

Prompt templates are useful, but they are not stable enough to drive repeated execution across multiple phases.

The initiative spec gives `supernb` one place to read:

- goal
- repository
- platform
- stack
- product category
- markets
- research window
- locales
- quality bar
- constraints

## Generated Files

When you run:

```bash
./scripts/supernb init-initiative my-product "My Product"
```

`supernb` now creates:

- `artifacts/initiatives/<initiative-id>.md`
- `artifacts/initiatives/<initiative-id>/initiative.yaml`
- `artifacts/initiatives/<initiative-id>/run-status.md`
- `artifacts/initiatives/<initiative-id>/next-command.md`
- `artifacts/initiatives/<initiative-id>/phase-packet.md`
- `artifacts/initiatives/<initiative-id>/run-log.md`
- `artifacts/initiatives/<initiative-id>/command-briefs/`
- `artifacts/initiatives/<initiative-id>/phase-results/`

## Runner Behavior

Run:

```bash
./scripts/supernb run --initiative-id <initiative-id>
```

The runner will:

- read `initiative.yaml`
- inspect current artifact approval fields
- compute which phase is blocked, ready, or complete
- write `run-status.md` and `run-status.json`
- generate `next-command.md` when the next phase is ready
- archive a timestamped brief for the selected phase
- write `phase-packet.md`
- append execution history to `run-log.md`

After phase execution, record the outcome with:

```bash
./scripts/supernb record-result \
  --initiative-id <initiative-id> \
  --status succeeded \
  --summary "Research batch completed"
```

That command writes a timestamped phase result, appends to `run-log.md`, and reruns `supernb run` by default.

When the phase should really advance, apply the gate update:

```bash
./scripts/supernb advance-phase \
  --initiative-id <initiative-id> \
  --phase research \
  --status approved \
  --actor supernb
```

That command updates the relevant artifact status fields for the phase, writes a gate-update record into `phase-results/`, and reruns `supernb run` by default.

## Gate Fields In Artifact Templates

The runner uses explicit status fields from the initiative artifacts instead of guessing from file existence alone.

Examples:

- research files: `Status: pending|approved`
- PRD: `Approval status: pending|approved`
- design files: `Approval status: pending|approved`
- implementation plan: `Ready for execution: yes|no`
- implementation plan: `Delivery status: pending|verified`
- release readiness: `Release decision: pending|ready`

## Compatibility Note

The runner prefers `PyYAML` when it is available.

If `PyYAML` is not installed, `supernb` falls back to a built-in parser that supports the generated scalar mapping structure in `initiative.yaml`.

That means:

- editing field values is safe
- keeping the generated shape is recommended
- turning the file into a deeply custom YAML document may break the fallback parser
