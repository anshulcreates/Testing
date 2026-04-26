#!/usr/bin/env bash
set -e

echo ">>> Installing Python dependencies..."
pip install -r requirements.txt

export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/.playwright-browsers
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

echo ">>> Installing Playwright Chromium to: $PLAYWRIGHT_BROWSERS_PATH"
playwright install chromium

echo ">>> Verifying browser installation..."
ls "$PLAYWRIGHT_BROWSERS_PATH"
echo ">>> Build complete."
