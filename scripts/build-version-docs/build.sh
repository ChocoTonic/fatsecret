#!/usr/bin/env bash
# Thin wrapper around build.py. Useful as the workflow entrypoint and for
# anyone who prefers `bash scripts/build-legacy-docs/build.sh`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

STAGING="${STAGING:-$REPO_ROOT/legacy-staging}"

python3 "$HERE/build.py" --repo "$REPO_ROOT" --staging "$STAGING" "$@"
