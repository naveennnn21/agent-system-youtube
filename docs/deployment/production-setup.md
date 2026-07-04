# Production Setup Guide

## Services

Run these as independent services:

- FastAPI API
- React dashboard
- Celery worker
- Celery beat scheduler
- PostgreSQL
- Redis

## Local Production Compose

```bash
cp .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

Add observability:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml -f docker-compose.observability.yml up -d
```

Dashboard:

```text
http://localhost:3000
```

API:

```text
http://localhost:8000/docs
```

Grafana:

```text
http://localhost:3001
```

## CI/CD

The workflow at `.github/workflows/ci-cd.yml` runs:

- backend tests with PostgreSQL and Redis service containers
- frontend build
- Docker image build and push to GHCR
- optional AWS ECS deployment
- optional Render deployment hook
- optional Railway deployment

Configure required variables and secrets in `deploy/github/repository-variables.md`.

## Docker Images

API image:

```text
ghcr.io/<owner>/<repo>-api:<git-sha>
```

Dashboard image:

```text
ghcr.io/<owner>/<repo>-dashboard:<git-sha>
```

The Celery worker and Celery beat services use the same API image with different commands.

## AWS

Use ECS Fargate with:

- one service for API
- one service for dashboard
- one service for Celery worker
- one service for Celery beat
- RDS PostgreSQL
- ElastiCache Redis
- CloudWatch Logs
- ALB target groups for API and dashboard

Task definition templates are in `deploy/aws`.

## Render

Use the root `render.yaml` blueprint. Set `DATABASE_URL` manually using the async SQLAlchemy driver:

```text
postgresql+asyncpg://...
```

Set the dashboard build variable:

```text
VITE_API_BASE_URL=https://<api-service>.onrender.com/api/v1
```

## Railway

Create separate Railway services for API, worker, beat, and dashboard. Use the Railway configs described in `deploy/railway/README.md`.

Set:

```text
DATABASE_URL=postgresql+asyncpg://...
DATABASE_SYNC_URL=postgresql://...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
VITE_API_BASE_URL=https://<api-service-domain>/api/v1
```

## Monitoring And Logging

Production app logs are JSON when `APP_ENV=production`.

The observability overlay provides:

- Prometheus for container metrics
- cAdvisor for Docker container telemetry
- Loki for logs
- Promtail for Docker log shipping
- Grafana with Prometheus and Loki datasources

For AWS, use CloudWatch Logs from the ECS task definitions.

## Release Checklist

1. Set production `.env` or platform variables.
2. Run database migrations with `alembic upgrade head`.
3. Build and publish API/dashboard images.
4. Deploy API first.
5. Deploy worker and beat.
6. Deploy dashboard.
7. Confirm `/api/v1/health`, `/api/v1/health/ready`, and `/docs`.
8. Open the dashboard and confirm `/api/v1/dashboard/overview` loads.
9. Confirm Celery worker health and Beat schedule.
