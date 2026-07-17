# Local dev ergonomics. Recipes are POSIX-sh friendly.
# Run `make` (or `make help`) to list targets.

.DEFAULT_GOAL := help

.PHONY: help install dev api web web-lint web-typecheck web-test py-lint py-fmt py-typecheck test e2e build health hooks

help: ## List available targets
	@echo "Targets:"
	@echo "  install  Sync Python deps (uv) and install web deps (npm ci)"
	@echo "  dev      Boot the API and Vite dev server together (Ctrl-C stops both)"
	@echo "  api      Run just the FastAPI dev server (port 8000)"
	@echo "  web      Run just the Vite dev server (port 5173)"
	@echo "  web-lint      Lint the web app (eslint)"
	@echo "  web-typecheck Type-check the web app (svelte-check)"
	@echo "  web-test      Run the web unit tests (vitest)"
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

dev: ## Boot API + Vite together; Ctrl-C stops both cleanly
	@echo "Starting API (8000) and web (5173). Press Ctrl-C to stop both."
	@# Signal the uvicorn *parent* by PID (its --reload child dies with it); a
	@# whole-group `kill 0` would double-signal uvicorn's reloader → RecursionError
	@# + segfault on Ctrl-C. npm is put in its own group (setsid) so the vite child
	@# goes down with it. `exit 0` = clean shutdown, no `*** Error 130` from make.
	@api=""; web=""; \
	if command -v setsid >/dev/null 2>&1; then SG=setsid; else SG=""; fi; \
	stop() { trap '' INT TERM; echo; echo "Shutting down..."; \
	  kill -TERM "$$api" 2>/dev/null || true; \
	  { kill -TERM "-$$web" 2>/dev/null || kill -TERM "$$web" 2>/dev/null; } || true; \
	  wait; exit 0; }; \
	trap stop INT TERM; \
	uv run uvicorn app.main:app --app-dir api --reload --port 8000 & api=$$!; \
	$$SG npm --prefix web run dev & web=$$!; \
	wait

api: ## Run just the API dev server
	uv run uvicorn app.main:app --app-dir api --reload --port 8000

web: ## Run just the Vite dev server
	npm --prefix web run dev

web-lint: ## Lint the web app (eslint)
	npm --prefix web run lint

web-typecheck: ## Type-check the web app (svelte-check)
	npm --prefix web run check

web-test: ## Run the web unit tests (vitest)
	npm --prefix web run test:unit

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
