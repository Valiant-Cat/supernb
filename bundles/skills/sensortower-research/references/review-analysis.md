# Review Analysis Playbook

Use this file when the task is not just "download reviews" but "extract product insight from reviews."

## Goal

Turn raw review rows into:

- main complaint clusters
- main delight clusters
- version-specific regressions
- country-specific patterns
- recurring feature requests
- evidence snippets that can support a product or market research memo

## Recommended flow

1. Export the raw review dataset first.
2. Keep the filters narrow enough to preserve context:
   - by country
   - by date window
   - by rating segment
   - optionally by keyword inside reviews
3. Build an initial heuristic report with `review-insights`.
4. Manually inspect the review samples attached to each theme before writing conclusions.
5. When asked to summarize, separate:
   - symptom
   - likely root cause
   - user segment affected
   - severity
   - evidence count

## Good segmentations

### Regression check after an update

- Pull reviews from 14 days before and 14 days after the release.
- Compare:
  - negative review volume
  - version hotspots
  - stability and login/account themes

### Monetization check

- Filter negative reviews.
- Search for:
  - ads
  - subscription
  - price
  - refund
  - paywall

### Market-localization check

- Pull the same app for `US`, `JP`, `KR`, `DE`, and one long-tail market.
- Compare:
  - localization complaints
  - payment complaints
  - support expectations

### Creative-message fit check

- Pull recent ad creatives and reviews from the same period.
- Check whether the promise in ads matches the actual complaints or delight themes.
- Watch for:
  - misleading ad complaints
  - feature mismatch
  - over-promising

## Heuristic limits

- The bundled `review-insights` command is fast and useful, but it is still heuristic.
- Multilingual reviews and sarcasm can weaken theme detection.
- Treat the theme counts as triage, not as final truth.
- For important deliverables, read a sample of raw reviews from each large cluster.

## Output style for later summaries

Prefer concise evidence-backed bullets:

- `Problem`: what users say is broken
- `Who`: which cohort or market shows it
- `When`: which version or date range
- `Signal`: review count, rating skew, representative samples
- `Action`: product, growth, ASO, support, or monetization implication
