---
name: product-research-prd
description: Use when creating or refining a product idea, PRD, or feature scope, and the work must be grounded in competitor analysis, app metadata, reviews, feature requests, and anti-features from Sensor Tower data.
---

# Product Research PRD

This skill makes research mandatory before PRD finalization.

## Required Inputs

- product category or seed competitors
- target markets or countries
- research date window

## Required Workflow

1. Resolve apps or publishers first.
2. Pull only the smallest useful datasets.
3. Export raw data before summarizing.
4. Extract:
   - top capabilities competitors emphasize
   - top user complaints
   - top user delight clusters
   - explicit feature requests
   - anti-features and monetization pain points
5. Turn those findings into a PRD with citations to the research window.

## Tooling Rule

If the local `sensortower-research` skill is available, use it. Do not invent app intelligence from memory.

## Output Standard

The final PRD must separate:

- evidence-backed must-haves
- evidence-backed avoidances
- hypotheses that still need validation

If the evidence is weak, say so explicitly instead of pretending certainty.

## Template Rule

If this repo contains an initiative scaffold under `artifacts/`, prefer saving research and PRD outputs there for organization.

Do not discard or compress richer upstream-generated documents just to fit the local scaffold. The scaffold is a storage convention, not a cap on detail.
