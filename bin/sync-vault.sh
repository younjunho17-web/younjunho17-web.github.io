#!/usr/bin/env bash
# Convenience wrapper: sync vault → content/ then show git status.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 bin/sync-vault.py "$@"
git status --short content/ 2>/dev/null || true
