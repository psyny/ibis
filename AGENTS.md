# Ibis

Household finance app: people in a household add shared costs, and Ibis shows each month's totals per category and the fewest transfers needed to settle who owes whom.

Stack: FastAPI + SQLAlchemy + Alembic backend, React/Vite (TypeScript) frontend served by nginx, PostgreSQL 16. No queue or worker.

## Where things live

| Part | Location | Entry point |
|------|----------|-------------|
| Frontend | `frontend/` | `src/main.tsx` (`src/api/`, `src/pages/`, `src/components/`) |
| Backend API | `backend/ibis/` | `main.py` (`uvicorn main:app`, `PYTHONPATH=backend/ibis`) |
| Migrations | `backend/ibis/alembic/versions/` | |
| Tests | `backend/ibis/tests/` (`unit/`, `integration/`) | |

Backend layers, outside in: `api/` (thin HTTP routes, auth dependencies) → `services/` (use cases, HTTP-independent) → `repositories/` + `models/` (data). `domain/` holds pure rules (roles, money, settlement) with no database or HTTP code. Keep that separation.

## Docs to read when relevant

- `README.md`: setup, run scripts, main screens
- `docs/domain.md`: business rules (read before changing costs, splits, roles or settlement)
- `docs/railway.md`: deployment
- `docs/repo.md`: repository structure
- `frontend/guidelines/style_guide.md`: UI style (read before frontend changes)

## Commands

```sh
make up                  # start Postgres + API + frontend in Docker (http://localhost:3000, API docs :8000/docs)
make down                # stop
make be-tests            # backend unit + API tests on SQLite, no Docker needed
make be-tests-postgres   # same tests against the Docker Postgres test DB
make fe-build fe-tests   # frontend typecheck/build + unit tests
```

On Windows, `start.bat` / `stop.bat` / `status.bat` / `logs.bat` / `reset-db.bat` wrap the Docker commands. `reset-db.bat` and `make clean` delete local data.

`notversioned/` is gitignored and holds local notes.
