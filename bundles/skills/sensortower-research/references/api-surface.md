# Sensor Tower API Surface Notes

Use this file when the task needs a quick reminder of the endpoint map, auth behavior, or the verification status behind this skill.

## Verification status

- Official docs entry page: `https://app.sensortower.com/api/docs`
  - As of 2026-03-06, anonymous access can resolve to either a login page or a `401` sign-in error depending on the client path and headers.
- Structured docs endpoints:
  - `https://api.sensortower.com/swagger.json`
  - `https://api.sensortower.com/openapi.json`
  - `https://api.sensortower.com/api-docs`
  - As of 2026-03-06, anonymous access returns `401` with a sign-in error.
  - As of 2026-03-06, adding a valid `auth_token` to those JSON paths still returned `404`, so do not rely on them as a stable official export surface.
- Official docs text provided by the user:
  - Base URL: `https://api.sensortower.com`
  - Auth: `auth_token` query parameter
  - Headers: `x-api-usage-limit`, `x-api-usage-count`
  - Rate limit: `6 requests/second`
  - Changelog date: `2026-02-26`
- Recent open-source references used to reconstruct the gated surface:
  - `toller892/SensorTower_mcp`
  - `econosopher/sensortowerr`

Treat the open-source materials as current-but-secondary evidence. When a token is available, run `scripts/sensortower_cli.py docs` to verify the gated docs again.

## Auth guidance

- Prefer `auth_token` query auth first. That matches the official docs text and the newer MCP implementation.
- If a request fails with `401` or `403` under query auth, retry once with `Authorization: Bearer <token>`. Some client libraries use that style for parts of the API.
- Never hardcode tokens inside the skill. Use one of:
  - `SENSORTOWER_AUTH_TOKEN`
  - `SENSORTOWER_API_TOKEN`
  - `SENSOR_TOWER_API_TOKEN`
- Optional backup:
  - `SENSORTOWER_AUTH_TOKEN_BACKUP`
  - `SENSORTOWER_API_TOKEN_BACKUP`
  - `SENSOR_TOWER_API_TOKEN_BACKUP`

## Wrapped endpoints

These are wrapped directly by `scripts/sensortower_cli.py`.

| Task | Endpoint |
| --- | --- |
| Search app or publisher | `/v1/{store}/search_entities` |
| App metadata | `/v1/{os}/apps` |
| Downloads and revenue history | `/v1/{os}/sales_report_estimates` |
| Top apps by downloads or revenue | `/v1/{os}/sales_report_estimates_comparison_attributes` |
| Category rankings | `/v1/{os}/ranking` |
| Current keywords | `/v1/{os}/keywords/get_current_keywords` |
| Keyword research | `/v1/{os}/keywords/research_keyword` |
| User reviews | `/v1/{os}/review/get_reviews` |
| Review timeline summary | `/v1/{os}/review/app_history_summary` |
| Ratings breakdown | `/v1/{os}/review/get_ratings` |
| Advertising creatives | `/v1/{os}/ad_intel/creatives` |

## Useful extra endpoints for raw mode

These were present in the newer MCP swagger snapshots, but they are not wrapped as first-class commands because `raw` is enough.

| Task | Endpoint |
| --- | --- |
| Top advertisers/publishers by SOV | `/v1/{os}/ad_intel/top_apps` |
| Search an advertiser/publisher rank | `/v1/{os}/ad_intel/top_apps/search` |
| Top creatives | `/v1/{os}/ad_intel/creatives/top` |
| Featured creatives in store | `/v1/{os}/featured/creatives` |
| Featured impact | `/v1/{os}/featured/impacts` |
| Featured apps | `/v1/ios/featured/apps` |
| Featured today stories | `/v1/ios/featured/today/stories` |

## Parameters worth remembering

### `/v1/{os}/sales_report_estimates`

- Required:
  - at least one of `app_ids` or `publisher_ids`
  - `countries`
  - `date_granularity`
  - `start_date`
  - `end_date`
- Revenue is returned in cents.
- Query segmentation guidance from docs:
  - `daily`: keep windows to about one week
  - `weekly`: about three months
  - `monthly`: about one year
  - `quarterly`: about two years

### `/v1/{os}/sales_report_estimates_comparison_attributes`

- Core params:
  - `comparison_attribute`: `absolute`, `delta`, `transformed_delta`
  - `time_range`: `day`, `week`, `month`, `quarter`, `year`
  - `measure`: `units`, `revenue`
  - `category`
  - `date`
  - `regions`
- Useful option:
  - `data_model=DM_2025_Q2` for the newer estimate model

### `/v1/{os}/review/get_reviews`

- Key params:
  - `app_id`
  - `country`
  - optional `start_date`, `end_date`
  - optional `rating_filter`
  - optional `search_term`
  - optional `username`
  - `limit` up to `200`
  - `page`

### `/v1/{os}/ad_intel/creatives`

- Key params:
  - `app_ids`
  - `start_date`
  - `countries`
  - `networks`
  - `ad_types`
- Useful optional params:
  - `end_date`
  - `limit`
  - `page`
  - `display_breakdown`
  - `placements`

## Research workflow reminders

1. Resolve IDs first with `search`.
2. Pull metadata and store assets before interpreting metrics.
3. Pull `sales` or `top-apps` with the smallest useful date window.
4. Pull `creatives` with explicit `networks` and `ad_types`; do not assume defaults.
5. Pull `reviews` into JSON or CSV, then run `review-insights`.
6. Use `raw` for uncovered endpoints instead of inventing parameters.
