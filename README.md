# Ibis

Household finance: people in a household add shared costs, and Ibis shows each month's
totals per category and the fewest transfers needed to settle who owes whom.

Same architecture as Qdra: FastAPI + SQLAlchemy + Alembic backend, React/Vite frontend
served by nginx, PostgreSQL. No queue or worker is needed.

## Project structure

```
ibis/
├── docker-compose.yml            # Local dev: frontend (hot reload), API, Postgres
├── docker-compose.prod-local.yml # Production-like build on your machine
├── Makefile
├── docs/                         # Domain rules, Railway deploy, repo notes
├── frontend/                     # React/Vite web UI (mobile-first)
│   ├── Dockerfile / nginx.conf   # Production image
│   └── src/
│       ├── api/                  # Typed API client
│       ├── pages/                # Dashboard, Add/Edit cost, Settings, Account, Admin
│       └── components/           # Split table, category chart, cost list...
└── backend/
    ├── Dockerfile.api            # Runs migrations on startup if RUN_MIGRATIONS_ON_STARTUP=true
    └── ibis/
        ├── main.py               # API entry point
        ├── api/                  # HTTP routes (thin)
        ├── services/             # Use cases (HTTP-independent, reusable by future bots)
        ├── domain/               # Pure rules: roles, money, settlement algorithm
        ├── repositories/         # Query helpers
        ├── models/               # SQLAlchemy tables
        ├── schemas/              # Pydantic request/response models
        ├── alembic/              # Migrations
        └── tests/                # unit/ and integration/
```

## Quick start on Windows (Docker Desktop)

Double-click (or run from a terminal) in the `ibis` folder:

| Script | What it does |
|--------|--------------|
| `start.bat` | Builds and starts Postgres + API + frontend, waits until ready, opens http://localhost:3000 |
| `stop.bat` | Stops everything (data is kept) |
| `status.bat` | Shows which containers are running |
| `logs.bat` | Follows logs (`logs.bat backend-api` for one service) |
| `reset-db.bat` | Deletes all local data (asks you to type RESET) |
| `prod-local.bat` | Production-like build on http://localhost:8080 (`prod-local.bat stop` to stop) |

The scripts start Docker Desktop if it isn't running.

## Quick start (Docker)

```bash
make up        # or: docker compose up -d --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

**The first sign-in creates the admin account** with whatever login and password you type.
Then, as admin: create a household, open its settings, and add people.

## Quick start (no Docker)

```bash
# Backend
cd backend
python -m venv venv
venv/Scripts/python -m pip install -e ".[dev]"     # venv/bin/python on Linux/macOS
cd ibis
DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis ../venv/Scripts/alembic upgrade head
DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis ../venv/Scripts/uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Tests

```bash
make be-tests            # backend: unit + API flow tests on SQLite, no Docker needed
make be-tests-postgres   # same tests against the Docker Postgres test DB
make fe-build fe-tests   # frontend typecheck/build + unit tests
```

## Main screens

| URL | What |
|-----|------|
| `/h/:householdId` | Monthly costs: split table, costs per category, cost list. `?m=2026-10` picks a month |
| `/h/:householdId/add` | Add a cost. Shareable link (asks to sign in first if needed) |
| `/h/:householdId/costs/:costId` | Edit/delete a cost |
| `/h/:householdId/settings` | Managers: members, categories, descriptions, starting state, months |
| `/account` | Your name, payment info (transfer number, QR code), WhatsApp, email, password |
| `/admin` | App admin: households and accounts |

See [docs/domain.md](docs/domain.md) for the rules and [docs/railway.md](docs/railway.md) to deploy.
