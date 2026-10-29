# Deploying on Railway

Same setup as Qdra: three services in one Railway project.

## 1. Postgres
Add a **PostgreSQL** database. Railway exposes `DATABASE_URL` (a `postgres://` URL is fine).

## 2. Backend API
- Source: this repo, **Root directory** `backend`, **Dockerfile path** `Dockerfile.api`.
- Variables:

```
APP_ENV=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
JWT_SECRET_KEY=<long random string>
CORS_ORIGINS=https://<your-frontend>.up.railway.app
RUN_MIGRATIONS_ON_STARTUP=true
```

The container waits for Postgres, runs `alembic upgrade head`, then starts uvicorn on `$PORT`.
Health check path: `/health`.

## 3. Frontend
- Source: this repo, **Root directory** `frontend`, Dockerfile `Dockerfile`.
- Variable (used at build time): `VITE_API_URL=https://<your-api>.up.railway.app`
- nginx serves the built app and falls back to `index.html`, so links like
  `/h/<id>/add` work when shared.

## First run
Open the frontend and sign in with the login/password you want for the admin: the first
sign-in on an empty database creates the admin account.

## Migrations after model changes
```bash
make be-migration MSG="describe the change"   # against local Docker Postgres
```
Commit the new file in `backend/ibis/alembic/versions/`; Railway applies it on the next deploy.
