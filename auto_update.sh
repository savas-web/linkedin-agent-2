#!/bin/bash
AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENT_NAME="$1"

if [ -z "$CLIENT_NAME" ]; then
    echo "Usage: auto_update.sh <client_name>"
    exit 1
fi

PLIST_PATH="$HOME/Library/LaunchAgents/digital.rooney.$CLIENT_NAME.plist"

cd "$AGENT_DIR"

git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

echo "$(date): Update found, pulling..."
git pull origin main --quiet

echo "$(date): Restarting agent for $CLIENT_NAME..."
launchctl bootout gui/$(id -u) "$PLIST_PATH" 2>/dev/null || true
sleep 2
launchctl bootstrap gui/$(id -u) "$PLIST_PATH"
echo "$(date): Agent restarted."
