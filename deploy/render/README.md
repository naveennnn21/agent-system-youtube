# Render Deployment

Use the root `render.yaml` blueprint to create:

- `youtube-shorts-api`
- `youtube-shorts-worker`
- `youtube-shorts-beat`
- `youtube-shorts-dashboard`
- managed PostgreSQL
- managed Redis

Render provides a PostgreSQL URL without the SQLAlchemy async driver name. Set:

```text
DATABASE_SYNC_URL=<Render internal database URL>
DATABASE_URL=<same URL, but postgresql:// changed to postgresql+asyncpg://>
```

Set `VITE_API_BASE_URL` on the dashboard service to the public API URL plus `/api/v1`.
