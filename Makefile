# Makefile for link-server monorepo

.PHONY: install
install:
	@echo "Installing all dependencies with Poetry..."
	poetry install

.PHONY: update
update:
	@echo "Updating dependencies..."
	poetry update

# ============================================================================
# Requirements Generation System
# ============================================================================
#
# How it works:
#
# 1. Pattern Rule (below): Defines how to build any mess-%/requirements.txt
#    - Prerequisites: pyproject.toml and poetry.lock
#    - Only rebuilds when either file is newer than requirements.txt
#    - Extracts service name from path (mess-auth → auth)
#    - Runs: poetry export --with=mess-<service> to include:
#      * Core dependencies from [tool.poetry.dependencies]
#      * Service-specific dependencies from [tool.poetry.group.mess-<service>.dependencies]
#      * All transitive dependencies (automatically resolved by Poetry)
#
# 2. Requirements Target: Lists all requirements files as prerequisites
#    - Make checks each file and rebuilds only outdated ones
#
# 3. Poetry Groups (pyproject.toml):
#    ┌─────────────────┬────────────────────────────────────────┐
#    │   Directory     │          Poetry Group                  │
#    ├─────────────────┼────────────────────────────────────────┤
#    │ mess-auth/      │ [tool.poetry.group.mess-auth....]      │
#    │ mess-user/      │ [tool.poetry.group.mess-user....]      │
#    │ mess-message/   │ [tool.poetry.group.mess-message....]   │
#    └─────────────────┴────────────────────────────────────────┘
#
# Usage:
#   make requirements              - Generate all requirements.txt (if needed)
#   make mess-auth/requirements.txt - Generate only mess-auth requirements
#
# ============================================================================

# Pattern rule: Generate requirements.txt from Poetry groups
# Regenerates only when pyproject.toml or poetry.lock changes
mess-%/requirements.txt: pyproject.toml poetry.lock
	@echo "Generating $@..."
	poetry export -f requirements.txt -o $@ --with=mess-$(patsubst mess-%/requirements.txt,%,$@) --without-hashes

# Target to build all requirements files
.PHONY: requirements
requirements: mess-auth/requirements.txt mess-user/requirements.txt mess-message/requirements.txt
	@echo "✨ All requirements.txt files generated successfully!"

.PHONY: install-all
install-all: install
	@echo "✨ All dependencies installed!"
	@echo "💡 Run 'make requirements' to generate requirements.txt files"

.PHONY: auth
auth:
	@echo "Starting mess-auth service..."
	cd mess-auth && poetry run uvicorn mess_auth.main:app --reload --port 8001

.PHONY: user
user:
	@echo "Starting mess-user service..."
	cd mess-user && poetry run uvicorn mess_user.main:app --reload --port 8002

.PHONY: message
message:
	@echo "Starting mess-message service..."
	cd mess-message && poetry run uvicorn mess_message.main:app --reload --port 8003

.PHONY: lint
lint:
	@echo "Running linters..."
	poetry run ruff check .
	poetry run black --check .

.PHONY: format
format:
	@echo "Formatting code..."
	poetry run black .
	poetry run ruff check --fix .

.PHONY: clean
clean:
	@echo "Cleaning up..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache 2>/dev/null || true

.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make install       - Install all dependencies with Poetry"
	@echo "  make requirements  - Generate requirements.txt for all services"
	@echo "  make install-all   - Install deps and generate requirements.txt"
	@echo "  make auth          - Start mess-auth service"
	@echo "  make user          - Start mess-user service"
	@echo "  make message       - Start mess-message service"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean up cache files"

