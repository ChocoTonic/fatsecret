# -----------------------------
# Project: Fatsecret Python SDK (uv-based)
# -----------------------------

# Variables
PYTHON := uv run python
PYTEST := uv run pytest
SRC_DIR := src/fatsecret
TEST_DIR := tests
DOCS_DIR := docs

.DEFAULT_GOAL := help

# -----------------------------
# Setup
# -----------------------------
.PHONY: install sync clean

install:  ## Install project dependencies via uv
	@uv sync --all-extras
	@echo "✅ Dependencies installed using uv."

sync:  ## Sync environment with lockfile
	@uv sync
	@echo "🔄 Environment synced with uv.lock."

clean:  ## Remove build artifacts and caches
	rm -rf build dist *.egg-info .pytest_cache .coverage coverage.xml
	find $(SRC_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	find $(TEST_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	@echo "🧹 Cleaned build and cache files."

# -----------------------------
# Testing
# -----------------------------
.PHONY: test test-unit test-int coverage

test:  ## Run all tests
	@$(PYTEST) -v

test-unit:  ## Run only unit tests
	@$(PYTEST) -v $(TEST_DIR)/unit

test-int:  ## Run only integration tests
	@$(PYTEST) -v -m integration

coverage:  ## Run tests with coverage
	@uv run pytest --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=xml:coverage.xml
	@rm -f .coverage

# -----------------------------
# Linting / Formatting
# -----------------------------
.PHONY: lint fmt check

lint:  ## Run code style and lint checks
	@uv run ruff check $(SRC_DIR) $(TEST_DIR)

fmt:  ## Auto-format code (black + isort)
	@uv run black $(SRC_DIR) $(TEST_DIR)
	@uv run isort $(SRC_DIR) $(TEST_DIR)
	@echo "✨ Code formatted."

check: lint test  ## Run lint and tests

# -----------------------------
# Packaging
# -----------------------------
.PHONY: build release

build:  ## Build the project using uv
	@uv build
	@echo "📦 Package built in dist/"

release: build  ## Publish to PyPI using uv
	@uv publish

# -----------------------------
# Misc
# -----------------------------
.PHONY: help

help:  ## Show available make targets
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
