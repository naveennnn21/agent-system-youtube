# Analytics Agent

`AnalyticsAgent` collects YouTube performance metrics, stores normalized
snapshots in PostgreSQL, and builds aggregate reports for the learning system.

## Metrics

The agent tracks:

- views
- watch time
- average view duration
- retention from `averageViewPercentage`
- CTR when a CTR metric is present, such as `annotationClickThroughRate` or
  `impressionsClickThroughRate`
- subscribers gained
- likes, comments, and shares

## Collection

The production client uses:

- OAuth refresh-token authentication
- YouTube Analytics API v2 `reports.query`
- `dimensions=video`
- filters for uploaded YouTube video IDs

Collection can be triggered through:

- `POST /api/v1/analytics/collect`
- `collect_youtube_analytics_job(session)`
- the full LangGraph workflow analytics node

## Storage

Snapshots are stored in the existing `analytics` table. The agent upserts by:

- internal `video_id`
- platform `youtube_shorts`
- `snapshot_date`

The original YouTube payload is preserved in `raw_metrics`, including
`external_video_id`.

## Reporting APIs

- `GET /api/v1/analytics/videos/{video_id}`
- `GET /api/v1/analytics/report`
- `GET /api/v1/analytics/top-videos`

The reporting layer returns totals, weighted CTR/retention, subscribers gained,
top videos, and daily totals.
