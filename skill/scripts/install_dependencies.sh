#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  skill/scripts/install_dependencies.sh [--with-mlx|--skip-mlx]

Behavior:
  - Install required Python packages for this skill
  - Auto-install mlx-whisper on macOS Apple Silicon by default
  - --with-mlx forces mlx-whisper install
  - --skip-mlx disables mlx-whisper install
EOF
}

WITH_MLX="auto"
for arg in "$@"; do
  case "$arg" in
    --with-mlx) WITH_MLX="yes" ;;
    --skip-mlx) WITH_MLX="no" ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown arg: $arg" >&2
      usage
      exit 1
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "python3/python not found" >&2
  exit 1
fi

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m | tr '[:upper:]' '[:lower:]')"

echo "[deps] python: $PYTHON"
"$PYTHON" -m pip install -U pip setuptools wheel
"$PYTHON" -m pip install "faster-whisper>=1.0.0" "youtube-transcript-api>=0.6.0"

install_mlx="false"
if [[ "$WITH_MLX" == "yes" ]]; then
  install_mlx="true"
elif [[ "$WITH_MLX" == "auto" && "$OS" == "darwin" && ( "$ARCH" == "arm64" || "$ARCH" == "aarch64" ) ]]; then
  install_mlx="true"
fi

if [[ "$install_mlx" == "true" ]]; then
  echo "[deps] installing mlx-whisper"
  "$PYTHON" -m pip install "mlx-whisper>=0.4.0"
else
  echo "[deps] skip mlx-whisper (OS=$OS ARCH=$ARCH mode=$WITH_MLX)"
fi

echo "[deps] done"
