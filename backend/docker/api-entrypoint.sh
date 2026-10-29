#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS_ON_STARTUP" = "true" ]; then
  echo "RUN_MIGRATIONS_ON_STARTUP=true; waiting for Postgres to be ready..."

  # Extract host and port from DATABASE_URL
  DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:/]*\).*/\1/p')
  DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*@[^:]*:\([0-9]*\)\/.*/\1/p')

  if [ -z "$DB_HOST" ]; then
    DB_HOST="postgres"
  fi
  if [ -z "$DB_PORT" ]; then
    DB_PORT="5432"
  fi

  echo "Waiting for $DB_HOST:$DB_PORT..."
  max_retries=30
  retry_count=0

  while [ $retry_count -lt $max_retries ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
      echo "Postgres is ready!"
      break
    fi
    retry_count=$((retry_count + 1))
    echo "Postgres not ready yet, retrying ($retry_count/$max_retries)..."
    sleep 2
  done

  if [ $retry_count -eq $max_retries ]; then
    echo "ERROR: Postgres did not become ready after $max_retries retries"
    exit 1
  fi

  echo "Running migrations..."
  python scripts/run_migrations.py
else
  echo "RUN_MIGRATIONS_ON_STARTUP is not true; skipping migrations"
fi

exec "$@"
