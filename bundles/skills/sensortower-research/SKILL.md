---
name: sensortower-research
description: Query Sensor Tower APIs for iOS App Store and Google Play research, including app lookup, metadata, downloads, revenue, category rankings, keywords, advertising creatives, featured placement, ratings, and user reviews. Use when Codex needs Sensor Tower-backed market research, competitor analysis, app intelligence exports, review mining, or structured app research for mobile products.
---

# Sensor Tower Research

Use this skill to turn Sensor Tower into a repeatable research workflow instead of ad hoc endpoint guessing.

## Quick Start

1. Resolve the target app or publisher first.
2. Pull only the smallest useful dataset.
3. Export raw data before summarizing it.
4. Use the raw endpoint escape hatch when the wrapped command set is not enough.

Set a token in the environment before calling the API:

```bash
export SENSORTOWER_AUTH_TOKEN='st_your_token'
```

Optional backup token:

```bash
export SENSORTOWER_AUTH_TOKEN_BACKUP='st_your_backup_token'
```

The CLI also accepts `SENSORTOWER_API_TOKEN` and `SENSOR_TOWER_API_TOKEN` naming and can retry with bearer auth if query auth fails.

## Core Workflow

### 1. Resolve IDs

Use `search` before any deep pull when the request starts from an app name or publisher name.

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py \
  search \
  --term "TikTok" \
  --store unified \
  --entity-type app \
  --records-only
```

### 2. Pull the right dataset

Use the smallest command that matches the research question:

- app metadata: `metadata`
- downloads and revenue: `sales`
- top apps by category or growth: `top-apps`
- store rankings: `rankings`
- keywords and ASO research: `keywords`, `keyword-research`
- user review data: `reviews`, `review-summary`, `ratings`
- marketing creatives: `creatives`
- uncovered endpoints: `raw`

### 3. Export before interpreting

Prefer writing JSON or CSV into the current workspace, then summarize from that file.

Examples:

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py \
  sales \
  --os unified \
  --app-id 55c527c302ac64f9c0002b18 \
  --country WW \
  --date-granularity monthly \
  --start-date 2025-01-01 \
  --end-date 2025-12-31 \
  --output /tmp/app-sales.json
```

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py \
  reviews \
  --os ios \
  --app-id 284882215 \
  --country US \
  --start-date 2026-01-01 \
  --end-date 2026-02-29 \
  --all-pages \
  --format csv \
  --output /tmp/reviews.csv
```

### 4. Turn reviews into insight

Run the heuristic review analyzer after exporting reviews or point it directly at the API.

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py \
  review-insights \
  --input /tmp/reviews.csv \
  --report /tmp/review-insights.md
```

When writing the final analysis, do not stop at theme counts. Read sample reviews from the biggest negative clusters before concluding root causes.

## Raw Mode

Use `raw` when the official or mirrored docs show an endpoint that is not wrapped yet.

Example: top creatives.

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py \
  raw \
  --endpoint /v1/unified/ad_intel/creatives/top \
  --param date=2026-02-01 \
  --param period=month \
  --param category=6005 \
  --param country=US \
  --param network=TikTok \
  --param ad_types=video
```

Use repeated `--param key=value` when a parameter should be repeated. Use comma-joined values when the docs show array parameters with `explode: false`.

## Documentation Refresh

The official docs are gated. Before assuming a path changed, run:

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py docs
```

If a token is configured, the same command can save retrieved docs:

```bash
python3 /Users/jerryhu/.codex/skills/sensortower-research/scripts/sensortower_cli.py \
  docs \
  --save-dir /tmp/sensortower-docs
```

Use `/Users/jerryhu/.codex/skills/sensortower-research/references/api-surface.md` when you need the verified endpoint map and `/Users/jerryhu/.codex/skills/sensortower-research/references/review-analysis.md` when the task is specifically review mining.

## Research Rules

- Do not invent endpoint names or parameter names. Check the reference file or use `raw`.
- Keep requests narrow first. Sensor Tower responses can become large enough to fail in browsers and slower clients.
- Respect the documented limit of 6 requests per second.
- Export raw data first when the user wants a memo, insight deck, or competitor brief.
- For review mining, separate:
  - top complaint clusters
  - top delight clusters
  - version hotspots
  - country-specific issues
  - monetization complaints
  - feature requests
- When a claim matters, cite the exact query window and country mix used to produce it.
