# Initiative: {{TITLE}}

- Initiative ID: `{{INIT_ID}}`
- Created: `{{DATE_STAMP}}`
- Slug: `{{SLUG}}`

## Artifact Map

- Initiative spec: [artifacts/initiatives/{{INIT_ID}}/initiative.yaml](/Users/xiaomiao26_1_26/projects/supernb/artifacts/initiatives/{{INIT_ID}}/initiative.yaml)
- Run status: [artifacts/initiatives/{{INIT_ID}}/run-status.md](/Users/xiaomiao26_1_26/projects/supernb/artifacts/initiatives/{{INIT_ID}}/run-status.md)
- Next command: [artifacts/initiatives/{{INIT_ID}}/next-command.md](/Users/xiaomiao26_1_26/projects/supernb/artifacts/initiatives/{{INIT_ID}}/next-command.md)
- Phase packet: [artifacts/initiatives/{{INIT_ID}}/phase-packet.md](/Users/xiaomiao26_1_26/projects/supernb/artifacts/initiatives/{{INIT_ID}}/phase-packet.md)
- Run log: [artifacts/initiatives/{{INIT_ID}}/run-log.md](/Users/xiaomiao26_1_26/projects/supernb/artifacts/initiatives/{{INIT_ID}}/run-log.md)
- Archived command briefs: [artifacts/initiatives/{{INIT_ID}}/command-briefs](/Users/xiaomiao26_1_26/projects/supernb/artifacts/initiatives/{{INIT_ID}}/command-briefs)
- Research: [artifacts/research/{{INIT_ID}}](/Users/xiaomiao26_1_26/projects/supernb/artifacts/research/{{INIT_ID}})
- PRD: [artifacts/prd/{{INIT_ID}}](/Users/xiaomiao26_1_26/projects/supernb/artifacts/prd/{{INIT_ID}})
- Design: [artifacts/design/{{INIT_ID}}](/Users/xiaomiao26_1_26/projects/supernb/artifacts/design/{{INIT_ID}})
- I18n strategy: [artifacts/design/{{INIT_ID}}/i18n-strategy.md](/Users/xiaomiao26_1_26/projects/supernb/artifacts/design/{{INIT_ID}}/i18n-strategy.md)
- Plan: [artifacts/plans/{{INIT_ID}}](/Users/xiaomiao26_1_26/projects/supernb/artifacts/plans/{{INIT_ID}})
- Release: [artifacts/releases/{{INIT_ID}}](/Users/xiaomiao26_1_26/projects/supernb/artifacts/releases/{{INIT_ID}})

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
