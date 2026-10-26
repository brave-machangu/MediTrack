# MediTrack developer commands (MT-030). Each target wraps a command published in
# backend/README.md, frontend/README.md or AGENTS.md; the plan is docs/development-workflow.md §2.
# Needs GNU make, bash, Docker Compose v2, and uv and Node 22 for the test and lint targets.
SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

COMPOSE := docker compose
BASE_URL ?= http://localhost:8080
# Reported by /healthz and /readyz as the version (backend Dockerfile build arg, MT-021).
export GIT_SHA ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

.PHONY: help up down seed test test-backend test-frontend lint gen-api smoke

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

.env:
	cp .env.example .env
	@echo "Created .env from .env.example (local-only values)."

up: .env ## Build and start the whole stack, then wait until /readyz returns 200
	$(COMPOSE) up -d --build
	./scripts/smoke.sh --wait-only $(BASE_URL)
	@echo "MediTrack: $(BASE_URL)   Grafana: http://localhost:3000"

down: ## Stop the stack; the database volume is kept
	$(COMPOSE) down

seed: ## Load synthetic demo data (needs MT-019)
	@echo "make seed needs the seed command from MT-019 (#16); backend/README.md doesn't publish it yet." >&2
	@exit 1

test: test-backend test-frontend ## All backend and frontend tests

test-backend: ## Backend tests (pytest)
	cd backend && uv run pytest

test-frontend: ## Frontend tests (Vitest, single run)
	cd frontend && npm run test

# ruff format skips Markdown like CI does: ruff 0.17 also formats code blocks in .md files (#55).
lint: ## ruff + mypy, eslint + tsc, OpenAPI lint
	cd backend && uv run ruff check . && uv run ruff format --check --extend-exclude '*.md' . && uv run mypy app
	cd frontend && npm run lint && npm run typecheck
	npx --yes @redocly/cli@1.34.20 lint api/openapi.yaml

gen-api: ## Regenerate frontend/src/api/schema.d.ts from api/openapi.yaml
	cd frontend && npm run gen:api

smoke: ## End-to-end smoke test against BASE_URL (default http://localhost:8080)
	./scripts/smoke.sh $(BASE_URL)
