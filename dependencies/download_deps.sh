#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEELHOUSE="$ROOT_DIR/dependencies/wheelhouse"

mkdir -p "$WHEELHOUSE"
python -m pip download -r "$ROOT_DIR/requirements.txt" -d "$WHEELHOUSE"
echo "Downloaded dependencies to $WHEELHOUSE"