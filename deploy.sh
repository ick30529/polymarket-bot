#!/usr/bin/env bash
# deploy.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO_DIR/venv"

echo "Pulling latest code..."
git -C "$REPO_DIR" pull

echo "Installing dependencies..."
if [ ! -d "$VENV" ]; then
  python3.11 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -r "$REPO_DIR/requirements.txt"

echo "Restarting service..."
sudo systemctl restart polymarket-bot
sudo systemctl status polymarket-bot --no-pager
