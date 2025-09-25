#!/usr/bin/env bash

set -euo pipefail

# Download and prepare ffmpeg binary for macOS (Apple Silicon preferred)
# Usage: ./scripts/download_ffmpeg.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$ROOT_DIR/resources/ffmpeg"
BIN_PATH="$TARGET_DIR/ffmpeg"

echo "📥 Preparing ffmpeg in: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# Prefer Apple Silicon (arm64). Evermeet provides fresh builds.
# Note: If this URL changes, replace with a known-good static ffmpeg (arm64) URL.
FFMPEG_URL="https://github.com/eugeneware/ffmpeg-static/releases/download/b5.0.1/darwin-arm64"

echo "⬇️  Downloading ffmpeg (binary) from: $FFMPEG_URL"
curl -L -o ffmpeg "$FFMPEG_URL"

# Ensure executable bit and remove quarantine (if present)
chmod +x ffmpeg || true
if command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine ffmpeg 2>/dev/null || true
fi

echo "🔍 File info:"
file ffmpeg || true

ARCH_LINE="$(file -b ffmpeg || true)"
if [[ "$ARCH_LINE" != *"arm64"* ]]; then
  echo "⚠️  Warning: ffmpeg is not arm64. If you target Apple Silicon (M1+), use an arm64 binary."
fi

echo "✅ ffmpeg ready at: $BIN_PATH"
echo "   It will be bundled as: Contents/Resources/resources/ffmpeg/ffmpeg"

