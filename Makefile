# Local dev ergonomics. Recipes are POSIX-sh friendly.
# Run `make` (or `make help`) to list targets.

.DEFAULT_GOAL := help

.PHONY: help install dev api web test e2e build health hooks py-lint py-fmt py-typecheck

help: ## List available targets
	@echo "Targets:"
	@echo "  install  Sync Python deps (uv) and install web deps (npm ci)"
	@echo "  dev      Boot the API and Vite dev server together (Ctrl-C stops both)"
	@echo "  api      Run just the FastAPI dev server (port 8000)"
	@echo "  web      Run just the Vite dev server (port 5173)"
	@echo "  test     Run the pytest suite"
	@echo "  py-lint      Lint Python with ruff (uv run ruff check .)"
	@echo "  py-fmt       Format Python with ruff (uv run ruff format .)"
	@echo "  py-typecheck Type-check Python with mypy (uv run mypy)"
	@echo "  e2e      Run the root Playwright end-to-end tests"
	@echo "  build    Build the web app"
	@echo "  health   Curl the API health endpoint"
	@echo "  hooks    Install the git pre-push hook (core.hooksPath -> .githooks)"

install: ## Sync Python deps and install web deps
	uv sync
	npm --prefix web ci

dev: ## Boot API + Vite together; Ctrl-C stops both
	@echo "Starting API (8000) and web (5173). Press Ctrl-C to stop both."
	@trap 'kill 0' INT TERM; \
	uv run uvicorn app.main:app --app-dir api --reload --port 8000 & \
	npm --prefix web run dev & \
	wait

api: ## Run just the API dev server
	uv run uvicorn app.main:app --app-dir api --reload --port 8000

web: ## Run just the Vite dev server
	npm --prefix web run dev

test: ## Run the pytest suite
	uv run pytest

py-lint: ## Lint Python with ruff
	uv run ruff check .

py-fmt: ## Format Python with ruff
	uv run ruff format .

py-typecheck: ## Type-check Python with mypy
	uv run mypy

e2e: ## Run the root Playwright e2e tests
	npm run e2e

build: ## Build the web app
	npm --prefix web run build

health: ## Curl the API health endpoint
	curl -s http://localhost:8000/health

hooks: ## Install the git pre-push hook
	git config core.hooksPath .githooks
	@echo "Installed: core.hooksPath -> .githooks (pre-push runs pytest + web build)"
