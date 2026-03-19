# Initiative: {{TITLE}}

- Initiative ID: `{{INIT_ID}}`
- Created: `{{DATE_STAMP}}`
- Slug: `{{SLUG}}`

## Artifact Map

- Initiative spec: [.supernb/initiatives/{{INIT_ID}}/initiative.yaml](./{{INIT_ID}}/initiative.yaml)
- Run status: [.supernb/initiatives/{{INIT_ID}}/run-status.md](./{{INIT_ID}}/run-status.md)
- Next command: [.supernb/initiatives/{{INIT_ID}}/next-command.md](./{{INIT_ID}}/next-command.md)
- Phase packet: [.supernb/initiatives/{{INIT_ID}}/phase-packet.md](./{{INIT_ID}}/phase-packet.md)
- Run log: [.supernb/initiatives/{{INIT_ID}}/run-log.md](./{{INIT_ID}}/run-log.md)
- Archived command briefs: [.supernb/initiatives/{{INIT_ID}}/command-briefs](./{{INIT_ID}}/command-briefs)
- Phase results: [.supernb/initiatives/{{INIT_ID}}/phase-results](./{{INIT_ID}}/phase-results)
- Research: [.supernb/research/{{INIT_ID}}](../research/{{INIT_ID}})
- PRD: [.supernb/prd/{{INIT_ID}}](../prd/{{INIT_ID}})
- Design: [.supernb/design/{{INIT_ID}}](../design/{{INIT_ID}})
- I18n strategy: [.supernb/design/{{INIT_ID}}/i18n-strategy.md](../design/{{INIT_ID}}/i18n-strategy.md)
- Plan: [.supernb/plans/{{INIT_ID}}](../plans/{{INIT_ID}})
- Release: [.supernb/releases/{{INIT_ID}}](../releases/{{INIT_ID}})

## Current Phase

- [ ] Research
- [ ] PRD
- [ ] Design
- [ ] Planning
- [ ] Delivery
- [ ] Release

## Notes

- Use `product-research-prd` first.
- Use `ui-ux-governance` only after the PRD is evidence-backed.
- Use `autonomous-delivery` only after PRD and design approval.
- Keep `initiative.yaml` updated before each major phase handoff.
- Run `./scripts/supernb run --initiative-id {{INIT_ID}}` to compute gates and generate the next command brief.
