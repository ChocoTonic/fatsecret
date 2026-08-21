# -----------------------------
# Project: Fatsecret Python SDK (uv-based)
# -----------------------------

# Variables
PYTHON := uv run python
PYTEST := uv run pytest
SRC_DIR := src/fatsecret
TEST_DIR := tests
DOCS_DIR := docs
DOCS_PORT ?= 10161

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

.PHONY: test test-unit test-int

COV_OPTS := --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=xml:coverage.xml

test:  ## Run all tests with coverage
	@uv run pytest -s -vv $(COV_OPTS)
	@rm -f .coverage

test-unit:  ## Run only unit tests with coverage
	@uv run pytest -s -vv $(COV_OPTS) $(TEST_DIR)/unit
	@rm -f .coverage

test-int:  ## Run only integration tests with coverage
	@uv run pytest -s -vv $(COV_OPTS) -m integration
	@rm -f .coverage

# -----------------------------
# Linting / Formatting
# -----------------------------
.PHONY: lint fmt check

lint:  ## Run code style and lint checks
	@uv run ruff check $(SRC_DIR) $(TEST_DIR)

fmt:  ## Auto-format code (black + isort)
	@uv run black .
	@uv run isort .
	@echo "✨ Code formatted."

check: lint test  ## Run lint and tests

# -----------------------------
# OAS pipeline
# -----------------------------
.PHONY: oas-contract-check oas-regen-check oasdiff

oas-contract-check:  ## Validate the manual member-web facade contract
	@uv run pytest tests/unit/test_member_web_oas.py -q

oas-regen-check:  ## Verify pipeline output matches committed files
	@md5sum docs/api-spec/raw/*.yaml docs/api-spec/openapi.yaml src/fatsecret/resources/_generated/*.py > /tmp/before.md5
	@cd scripts/oas-sync && uv run oas-sync sync && \
	  for tag in "Foods" "Food Classification" "Recipes" "Profile Foods" \
	             "Saved Meals" "Food Diary" "Exercise Diary" "Weight Diary" \
	             "Profile Auth" "Native APIs" "Feedback"; do \
	      uv run oas-sync emit-resource "$$tag"; \
	  done
	@md5sum docs/api-spec/raw/*.yaml docs/api-spec/openapi.yaml src/fatsecret/resources/_generated/*.py > /tmp/after.md5
	@diff /tmp/before.md5 /tmp/after.md5 && echo "✓ pipeline output matches committed files" || (echo "✗ DRIFT — re-run the pipeline locally and commit the diffs"; exit 1)

oasdiff:  ## Diff openapi.yaml against origin/master
	@oasdiff breaking <(git show origin/master:docs/api-spec/openapi.yaml) docs/api-spec/openapi.yaml --fail-on ERR

# -----------------------------
# Packaging
# -----------------------------
.PHONY: build release

build:  ## Build the project using uv
	rm -rf build dist *.egg-info
	find $(SRC_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	find $(TEST_DIR) -type d -name "__pycache__" -exec rm -rf {} +
	@uv build
	@echo "📦 Package built in dist/"

release: build  ## Publish to PyPI using uv
	@uv publish

# -----------------------------
# Misc
# -----------------------------
.PHONY: help all example docs docs-serve

example: fmt lint  ## Run the CLI example end-to-end against the live FatSecret API (.env required)
	@PYTHONPATH=src uv run python examples/main.py

docs:  ## Build Sphinx documentation
	@rm -rf $(DOCS_DIR)/_build
	@uv run sphinx-build -b html -W $(DOCS_DIR) $(DOCS_DIR)/_build/html

serve: docs  ## Build then serve docs on localhost:10161 (override with DOCS_PORT=<port>)
	@echo "Serving docs at http://localhost:$(DOCS_PORT) (Ctrl+C to stop)"
	@cd docs/_build/html && $(PYTHON) -m http.server $(DOCS_PORT)

help:  ## Show available make targets
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

all: fmt lint test  ## Run formatting, linting, and all tests
	@echo "✅ All checks (format, lint, test) passed."
