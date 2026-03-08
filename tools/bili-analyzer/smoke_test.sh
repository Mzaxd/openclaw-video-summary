#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[1/4] CLI help"
python3 -m bili_analyzer.cli --help >/dev/null

echo "[2/4] prepare help"
python3 -m bili_analyzer.cli prepare --help >/dev/null

echo "[3/4] analyze-frames basic"
TMP_DIR="$(mktemp -d)"
mkdir -p "$TMP_DIR/images"
touch "$TMP_DIR/images/frame_000001.jpg"
touch "$TMP_DIR/images/frame_000002.jpg"
python3 -m bili_analyzer.cli analyze-frames "$TMP_DIR/images" >/dev/null

if [[ ! -f "$TMP_DIR/images/frames_index.json" ]]; then
  echo "frames_index.json not generated"
  exit 1
fi

echo "[4/4] mcp import"
python3 - <<'PY'
import importlib.util
import sys

if importlib.util.find_spec("mcp") is None:
    print("mcp dependency not installed; skipping MCP import check")
    sys.exit(0)

import bili_analyzer.mcp_server  # noqa: F401
print("mcp module import ok")
PY

echo "Smoke test passed"
