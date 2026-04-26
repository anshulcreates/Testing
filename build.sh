#!/usr/bin/env bash
set -e

echo ">>> Installing Python dependencies..."
pip install -r requirements.txt

echo ">>> Installing Chromium system libraries..."
apt-get update -qq && apt-get install -y -qq \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 \
  libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
  libgbm1 libxkbcommon0 libpango-1.0-0 libcairo2 libasound2 \
  || echo "Some system libs already present, continuing..."

export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright-browsers
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

echo ">>> Installing Playwright Chromium to: $PLAYWRIGHT_BROWSERS_PATH"
playwright install chromium

echo ">>> Verifying browser installation..."
ls "$PLAYWRIGHT_BROWSERS_PATH"
echo ">>> Build complete."
