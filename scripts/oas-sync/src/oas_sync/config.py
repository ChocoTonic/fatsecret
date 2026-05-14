from __future__ import annotations

from pathlib import Path

DOCS_BASE = "https://platform.fatsecret.com"
DOCS_ROOT = f"{DOCS_BASE}/docs"
GUIDES_HUB = f"{DOCS_ROOT}/guides"

VERSIONS_TO_PROBE = ("v1", "v2", "v3", "v4", "v5", "v6")

LANDING_MARKER = "Welcome to the fatsecret Platform REST API"

# Resolve paths from this file's location:
#   .../pyfatsecret-chocotonic/scripts/oas-sync/src/oas_sync/config.py
#   parents[0] = oas_sync/, [1] = src/, [2] = oas-sync/, [3] = scripts/, [4] = repo root
PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # the oas-sync project dir
REPO_ROOT = Path(__file__).resolve().parents[4]

CACHE_DIR = PACKAGE_ROOT / ".cache"
OUT_INVENTORY = REPO_ROOT / "docs" / "api-inventory.md"
OUT_RAW_DIR = REPO_ROOT / "docs" / "api-spec" / "raw"
OUT_OPENAPI = REPO_ROOT / "docs" / "api-spec" / "openapi.generated.yaml"

USER_AGENT = "pyfatsecret-oas-sync/0.1 (+https://github.com/ChocoTonic/pyfatsecret)"
REQUEST_TIMEOUT_S = 30.0
