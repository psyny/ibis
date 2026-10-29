.PHONY: help up down build logs logs-api ps clean restart-soft restart-hard db-reset
.PHONY: prod-local-up prod-local-down prod-local-clean
.PHONY: be-venv be-install be-tests be-tests-postgres be-migration fe-install fe-build fe-tests

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ============================================================================
# Docker
# ============================================================================

up: ## Start all services (migrations run on API startup)
	docker compose up -d
	@echo ""
	@echo "Frontend: http://localhost:3000   API: http://localhost:8000/docs"
	@echo "First sign-in creates the admin account."

down: ## Stop all services
	docker compose down

build: ## Build all services
	docker compose build

logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show logs from backend-api
	docker compose logs -f backend-api

ps: ## Show running containers
	docker compose ps

restart-soft: ## Restart (down, up)
	$(MAKE) down
	$(MAKE) up

restart-hard: ## Rebuild and restart
	$(MAKE) down
	$(MAKE) build
	$(MAKE) up

clean: ## Stop and remove containers AND volumes (deletes local data)
	docker compose down -v

db-reset: ## Drop and recreate the local database
	docker compose up -d postgres
	@sleep 3
	docker compose exec postgres psql -U ibis -d postgres -c "DROP DATABASE IF EXISTS ibis;"
	docker compose exec postgres psql -U ibis -d postgres -c "CREATE DATABASE ibis;"

# ============================================================================
# Production-like local test (GET http://localhost:8000/health, http://localhost:8080)
# ============================================================================

prod-local-up: ## Start production-like environment
	docker compose -f docker-compose.prod-local.yml up --build

prod-local-down: ## Stop production-like environment
	docker compose -f docker-compose.prod-local.yml down

prod-local-clean: ## Stop production-like environment and delete its data
	docker compose -f docker-compose.prod-local.yml down -v

# ============================================================================
# Backend
# ============================================================================

BE_DIR := backend
BE_VENV := $(BE_DIR)/venv
ifeq ($(OS),Windows_NT)
  BE_BIN := $(BE_VENV)/Scripts
else
  BE_BIN := $(BE_VENV)/bin
endif

be-venv: ## Create backend virtual environment
	python -m venv $(BE_VENV)

be-install: ## Install backend dependencies (dev included)
	@if [ ! -d "$(BE_VENV)" ]; then python -m venv $(BE_VENV); fi
	$(BE_BIN)/python -m pip install --upgrade pip
	$(BE_BIN)/python -m pip install -e "$(BE_DIR)[dev]"

be-tests: ## Run backend tests on SQLite (no Docker). Optional: TARGET=unit/test_settlement.py
	cd $(BE_DIR) && ./$(subst $(BE_DIR)/,,$(BE_BIN))/python -m pytest ibis/tests/$(TARGET) -v

be-tests-postgres: ## Run backend tests against the Docker Postgres test DB
	cd $(BE_DIR) && TEST_DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis_test ./$(subst $(BE_DIR)/,,$(BE_BIN))/python -m pytest ibis/tests -v

be-migration: ## Autogenerate a migration after model changes. Usage: make be-migration MSG="add x"
	cd $(BE_DIR)/ibis && DATABASE_URL=postgresql://ibis:ibis@localhost:5432/ibis ../$(subst $(BE_DIR)/,,$(BE_BIN))/alembic revision --autogenerate -m "$(MSG)"

# ============================================================================
# Frontend
# ============================================================================

fe-install: ## Install frontend dependencies
	cd frontend && npm install

fe-build: ## Typecheck and build the frontend
	cd frontend && npm run build

fe-tests: ## Run frontend unit tests
	cd frontend && npx vitest run
