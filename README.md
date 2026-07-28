# 🎬 Autonomous YouTube Shorts AI Agent

An autonomous AI agent system that **researches**, **scripts**, **reviews**, and **produces** YouTube Shorts content — powered by LangGraph, LangChain, FastAPI, PostgreSQL, and Redis.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Gateway                        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  Health   │  │  API v1/v2   │  │  WebSocket (future)   │ │
│  └──────────┘  └──────────────┘  └───────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────────┐
   │ LangGraph│   │PostgreSQL│   │    Redis      │
   │  Agent   │   │   (DB)   │   │  (Cache/Q)   │
   └────┬─────┘   └──────────┘   └──────────────┘
        │
  ┌─────┼─────────────┐
  ▼     ▼             ▼
┌────┐┌──────┐  ┌──────────┐
│ Re-││Script│  │  Review  │
│search│ Node │  │   Node   │
└────┘└──────┘  └──────────┘
```

The **LangGraph agent** follows a linear pipeline:

1. **Research Node** — gathers trending topics, keywords, and competitor data.
2. **Script Node** — drafts a short-form video script using an LLM chain.
3. **Review Node** — scores and provides feedback on the draft.

---

## 🛠️ Tech Stack

| Layer          | Technology                           |
| -------------- | ------------------------------------ |
| API Framework  | FastAPI 0.110+                       |
| Agent Runtime  | LangGraph + LangChain                |
| LLM Provider   | OpenAI (GPT-4o) / configurable       |
| Database       | PostgreSQL 16 + asyncpg              |
| Migrations     | Alembic (async)                      |
| Cache / Queue  | Redis 7                              |
| ORM            | SQLAlchemy 2.0 (async)               |
| Validation     | Pydantic v2                          |
| Containerisation | Docker + Docker Compose            |
| Testing        | pytest + pytest-asyncio + httpx      |
| Linting        | ruff · mypy                          |

---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (recommended)
- **PostgreSQL 16** and **Redis 7** (if running locally without Docker)

### 1. Docker (recommended)

```bash
# Clone the repository
git clone https://github.com/<your-org>/agent-system-youtube.git
cd agent-system-youtube

# Copy the example environment file and fill in secrets
cp .env.example .env

# Build and start all services
docker compose up --build -d

# Run database migrations
docker compose exec app alembic upgrade head

# Verify
curl http://localhost:8000/api/v1/health
```

### 2. Local Development

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or use a .env file)
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/youtube_agent"
export REDIS_URL="redis://localhost:6379/0"

# Run database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📁 Project Structure

```
agent-system-youtube/
├── alembic/                    # Database migrations
│   ├── env.py                  #   Async migration environment
│   ├── script.py.mako          #   Migration template
│   └── versions/               #   Generated migration files
│       └── .gitkeep
├── alembic.ini                 # Alembic configuration
├── app/
│   ├── agents/                 # LangGraph agent definitions
│   │   ├── __init__.py
│   │   └── graph.py            #   Research → Script → Review pipeline
│   ├── api/                    # FastAPI routers
│   │   ├── __init__.py
│   │   ├── router.py           #   Root router (includes sub-routers)
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py       #   Liveness & readiness probes
│   ├── core/                   # Configuration & settings
│   │   ├── __init__.py
│   │   └── config.py
│   ├── db/                     # Database & Redis connections
│   │   ├── __init__.py
│   │   ├── base.py             #   Declarative Base
│   │   ├── redis.py            #   Async Redis manager
│   │   └── session.py          #   Async SQLAlchemy session
│   ├── main.py                 # Application entry point
│   ├── models/                 # SQLAlchemy ORM models
│   │   └── __init__.py
│   ├── schemas/                # Pydantic request / response schemas
│   │   └── __init__.py
│   └── services/               # Business logic services
│       ├── __init__.py
│       └── youtube/
│           └── __init__.py
├── docker-compose.yml
├── Dockerfile
├── README.md
├── requirements.txt
└── tests/
    ├── __init__.py
    └── conftest.py             # Shared pytest fixtures
```

---

## 🔌 API Endpoints

| Method | Path                | Description                                     |
| ------ | ------------------- | ----------------------------------------------- |
| GET    | `/`                 | Welcome message + quick links                   |
| GET    | `/api/v1/health`    | Lightweight liveness probe                      |
| GET    | `/api/v1/health/ready` | Deep readiness check (DB + Redis)            |
| GET    | `/docs`             | Interactive Swagger UI                          |
| GET    | `/redoc`            | ReDoc API documentation                         |

---

## 🔄 Development Workflow

```bash
# 1. Create a new feature branch
git checkout -b feat/my-feature

# 2. Make changes and run lint
ruff check . --fix
mypy app/

# 3. Run the test suite
pytest -v

# 4. Generate a migration (if models changed)
alembic revision --autogenerate -m "add my_table"
alembic upgrade head

# 5. Commit and push
git add .
git commit -m "feat: add my_table model"
git push origin feat/my-feature
```

---

## ⚙️ Environment Variables

| Variable               | Description                                  | Default / Example                                          |
| ---------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| `DATABASE_URL`         | Async PostgreSQL connection string           | `postgresql+asyncpg://postgres:postgres@db:5432/youtube_agent` |
| `DATABASE_SYNC_URL`    | Sync PostgreSQL URL (Alembic CLI)            | `postgresql://postgres:postgres@db:5432/youtube_agent`     |
| `REDIS_URL`            | Redis connection string                      | `redis://redis:6379/0`                                     |
| `REDIS_MAX_CONNECTIONS`| Max connections in the Redis pool            | `10`                                                       |
| `CORS_ORIGINS`         | Comma-separated list of allowed origins      | `["http://localhost:3000"]`                                |
| `OPENAI_API_KEY`       | OpenAI API key for LLM calls                | *(required)*                                               |
| `LOG_LEVEL`            | Python logging level                         | `INFO`                                                     |
| `ENV`                  | Environment name (`development`, `production`) | `development`                                            |

---

## 📄 License

This project is licensed under the **MIT License**.

| `RATE_LIMIT_ENABLED`      | Enable API rate limiting                         | `true`                                    |
| `RATE_LIMIT_DEFAULT`      | Default rate limit for all endpoints             | `60/minute`                               |
| `RATE_LIMIT_AUTOMATION`   | Rate limit for automation endpoints              | `10/minute`                               |
| `RATE_LIMIT_ANALYTICS`    | Rate limit for analytics endpoints               | `20/minute`                               |
