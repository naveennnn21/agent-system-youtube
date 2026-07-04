# GitHub Actions Configuration

Repository variables:

```text
VITE_API_BASE_URL

AWS_REGION
AWS_ECS_CLUSTER
AWS_API_SERVICE
AWS_WORKER_SERVICE
AWS_BEAT_SERVICE
AWS_DASHBOARD_SERVICE

RENDER_DEPLOY_ENABLED=true

RAILWAY_DEPLOY_ENABLED=true
RAILWAY_API_SERVICE
RAILWAY_WORKER_SERVICE
RAILWAY_BEAT_SERVICE
RAILWAY_DASHBOARD_SERVICE
```

Repository secrets:

```text
AWS_ROLE_TO_ASSUME
RENDER_DEPLOY_HOOK_URL
RAILWAY_TOKEN
```

The CI workflow always runs backend and frontend validation. Image publishing and deploy jobs run only on `main`, not on pull requests.
