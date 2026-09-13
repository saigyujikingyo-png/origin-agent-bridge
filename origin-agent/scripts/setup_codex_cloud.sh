#!/usr/bin/env bash
set -euo pipefail

# Reuse this script for initial setup and cached-container maintenance.
package_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$package_dir"

if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'uv is required. Use the Codex universal image with uv installed.' >&2
    exit 1
fi

uv sync --locked --python 3.12
printf '%s\n' 'Cloud development dependencies ready. Native Origin tests require a licensed Windows executor.'
