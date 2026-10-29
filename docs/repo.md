# Repository structure

| Service | Location | Entry point |
|---------|----------|-------------|
| Frontend web UI | `frontend/` | `src/main.tsx` |
| Backend API | `backend/ibis/` | `main.py` (`uvicorn main:app`, `PYTHONPATH=backend/ibis`) |
| Database | Postgres 16 | migrations in `backend/ibis/alembic/versions/` |

Backend layers, outside in: `api/` (HTTP, auth dependencies) → `services/` (use cases) →
`repositories/` + `models/` (data) with `domain/` holding pure rules (roles, money, settlement)
that have no database or HTTP code.

`notversioned/` is gitignored for local notes.
