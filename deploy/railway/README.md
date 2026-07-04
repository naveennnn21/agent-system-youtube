# Railway Deployment

Create separate Railway services for:

- API: use root `railway.json`
- Celery worker: copy `deploy/railway/worker.railway.json` to the service as `railway.json`
- Celery beat: copy `deploy/railway/beat.railway.json` to the service as `railway.json`
- Dashboard: use `frontend/railway.json` with root directory `frontend`

Add Railway PostgreSQL and Redis plugins, then set:

```text
DATABASE_SYNC_URL=<Railway Postgres URL>
DATABASE_URL=<same URL, but postgresql:// changed to postgresql+asyncpg://>
REDIS_URL=<Railway Redis URL>
CELERY_BROKER_URL=<Railway Redis URL>
CELERY_RESULT_BACKEND=<Railway Redis URL>
VITE_API_BASE_URL=https://<api-service-domain>/api/v1
```
