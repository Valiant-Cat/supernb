# Initiative Spec

`supernb` now uses a per-initiative control file:

- `.supernb/initiatives/<initiative-id>/initiative.yaml` inside the active product workspace by default

This file is the single source of truth for the runner.

## Why It Exists

Prompt templates are useful, but they are not stable enough to drive repeated execution across multiple phases.

The initiative spec gives `supernb` one place to read:

- goal
- repository
- project directory
- harness preference
- platform
- stack
- product category
- markets
- research window
- locales
- scale target
- quality bar
- constraints

## Generated Files

When you run:

```bash
./scripts/supernb init-initiative my-product "My Product"
```

`supernb` now creates:

- `.supernb/initiatives/<initiative-id>.md`
- `.supernb/initiatives/<initiative-id>/initiative.yaml`
- `.supernb/initiatives/<initiative-id>/run-status.md`
- `.supernb/initiatives/<initiative-id>/run-status.json`
- `.supernb/initiatives/<initiative-id>/certification-state.json`
- `.supernb/initiatives/<initiative-id>/next-command.md`
- `.supernb/initiatives/<initiative-id>/phase-packet.md`
- `.supernb/initiatives/<initiative-id>/run-log.md`
- `.supernb/initiatives/<initiative-id>/command-briefs/`
- `.supernb/initiatives/<initiative-id>/phase-results/`
- `.supernb/initiatives/<initiative-id>/executions/`

## Runner Behavior

Run:

```bash
./scripts/supernb run --initiative-id <initiative-id>
```

The runner will:

- read `initiative.yaml`
- inspect current artifact approval fields and certification state
- compute which phase is blocked, ready, or complete
- write `run-status.md` and `run-status.json`
- generate `next-command.md` when the next phase is ready
- archive a timestamped brief for the selected phase
- write `phase-packet.md`
- append execution history to `run-log.md`

To bridge the rendered prompt into a supported harness CLI, use:

```bash
./scripts/supernb execute-next \
  --initiative-id <initiative-id> \
  --harness codex \
  --project-dir /path/to/repo
```

That command copies the current prompt into a timestamped execution packet, invokes the harness when supported, and records stdout/stderr/response artifacts under `executions/`.

Each execution packet now also includes:

- `result-suggestion.json`
- `result-suggestion.md`

`--dry-run` packets are preview-only, and `certify-phase` now prefers the latest real non-dry-run packet when evaluating planning and delivery readiness.
For direct Codex and Claude Code bridging, the captured response must include the `REPORT JSON` block or the packet will be downgraded to `needs-follow-up`.

You can apply that packet back into the initiative with:

```bash
./scripts/supernb apply-execution \
  --initiative-id <initiative-id> \
  --packet /path/to/execution-packet
```

That command turns the packet into a recorded phase result, and can optionally run certification or certification+gate apply.

For OpenCode or other manual handoff flows, import a structured execution result into a normal packet first:

```bash
./scripts/supernb import-execution \
  --initiative-id <initiative-id> \
  --phase delivery \
  --report-json /path/to/report.json
```

`import-execution` now validates every declared `evidence_artifacts` path before it writes the packet.

After phase execution, record the outcome with:

```bash
./scripts/supernb record-result \
  --initiative-id <initiative-id> \
  --status needs-follow-up \
  --summary "Research batch completed" \
  --source manual-override \
  --override-reason "Packet evidence was incomplete"
```

That command writes a timestamped phase result, appends to `run-log.md`, and reruns `supernb run` by default. Manual use is now treated as a controlled override path rather than a peer of execution packets.

When the phase should really advance, apply the gate update:

```bash
./scripts/supernb advance-phase \
  --initiative-id <initiative-id> \
  --phase research \
  --status approved \
  --actor supernb
```

That command updates the relevant artifact status fields for the phase, writes a gate-update record into `phase-results/`, and reruns `supernb run` by default.

Before advancing, you can ask `supernb` to inspect the artifacts for unresolved scaffold placeholders, missing sections, thin sections, and phase-specific semantic gaps:

```bash
./scripts/supernb certify-phase \
  --initiative-id <initiative-id> \
  --phase research
```

If no issues are found, it recommends the expected gate status. With `--apply`, it also advances the gate automatically.

Current default initiative posture:

- `delivery.scale_target_dau` defaults to `10000000`
- `delivery.quality_bar` defaults to `10m-dau-grade`
- PRD, design, implementation plan, and release readiness are expected to carry aligned cross-phase traceability matrices with stable `Trace ID` rows
- old initiatives can be brought forward with `./scripts/supernb upgrade-artifacts --initiative-id <initiative-id>`
- pre-initiative loose workspaces can be imported with `./scripts/supernb migrate-legacy --initiative-id <initiative-id>`
- legacy imports now include `legacy-mapping.md/json` so reconciliation starts from suggested target artifacts instead of ad hoc copying
- stale dry runs, unsupported packets, and older execution artifacts can be previewed or archived with `./scripts/supernb clean-initiative --initiative-id <initiative-id> [--apply]`
- hard deletion is now explicit: `./scripts/supernb clean-initiative --initiative-id <initiative-id> --apply --delete`

## Gate Fields In Artifact Templates

The runner uses explicit status fields from the initiative artifacts instead of guessing from file existence alone.

Examples:

- research files: `Status: pending|approved`
- PRD: `Approval status: pending|approved`
- design files: `Approval status: pending|approved`
- implementation plan: `Ready for execution: yes|no`
- implementation plan: `Delivery status: pending|verified`
- release readiness: `Release decision: pending|ready`

Those fields are not sufficient on their own. Phase completion also requires a matching passing certification record in `certification-state.json`.

## Compatibility Note

The runner prefers `PyYAML` when it is available.

If `PyYAML` is not installed, `supernb` falls back to a built-in parser that supports the generated scalar mapping structure in `initiative.yaml`.

That means:

- editing field values is safe
- keeping the generated shape is recommended
- turning the file into a deeply custom YAML document may break the fallback parser
