# AWS ECS Deployment

This directory contains ECS Fargate task definitions for:

- API service: `api-task-definition.json`
- Celery worker service: `worker-task-definition.json`
- Celery beat service: `beat-task-definition.json`
- Dashboard service: `dashboard-task-definition.json`

Expected AWS resources:

- ECS cluster
- Four ECS services
- Application Load Balancer target group for the API on port `8000`
- Application Load Balancer target group for the dashboard on port `80`
- RDS PostgreSQL
- ElastiCache Redis
- CloudWatch log group: `/ecs/youtube-shorts-agent`
- ECS execution role
- ECS task role
- GitHub OIDC role used by CI/CD

Store production settings in SSM Parameter Store or Secrets Manager under:

```text
/youtube-shorts-agent/DATABASE_URL
/youtube-shorts-agent/DATABASE_SYNC_URL
/youtube-shorts-agent/REDIS_URL
/youtube-shorts-agent/CELERY_BROKER_URL
/youtube-shorts-agent/CELERY_RESULT_BACKEND
/youtube-shorts-agent/OPENAI_API_KEY
/youtube-shorts-agent/ANTHROPIC_API_KEY
/youtube-shorts-agent/ELEVENLABS_API_KEY
/youtube-shorts-agent/FLUX_API_KEY
/youtube-shorts-agent/STABILITY_API_KEY
/youtube-shorts-agent/YOUTUBE_API_KEY
/youtube-shorts-agent/YOUTUBE_OAUTH_CLIENT_ID
/youtube-shorts-agent/YOUTUBE_OAUTH_CLIENT_SECRET
/youtube-shorts-agent/YOUTUBE_OAUTH_REFRESH_TOKEN
/youtube-shorts-agent/CORS_ORIGINS
```

GitHub repository variables for AWS deployment:

```text
AWS_REGION
AWS_ECS_CLUSTER
AWS_API_SERVICE
AWS_WORKER_SERVICE
AWS_BEAT_SERVICE
AWS_DASHBOARD_SERVICE
```

GitHub repository secret:

```text
AWS_ROLE_TO_ASSUME
```

Before first deploy, replace `ACCOUNT_ID` and `us-east-1` placeholders in the task definitions.
