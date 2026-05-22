#!/bin/bash
AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENT_NAME="$1"

if [ -z "$CLIENT_NAME" ]; then
    echo "Usage: auto_update.sh <client_name>"
    exit 1
fi

PLIST_PATH="$HOME/Library/LaunchAgents/digital.rooney.$CLIENT_NAME.plist"
ENV_FILE="$AGENT_DIR/.env"

cd "$AGENT_DIR"

GITHUB_TOKEN="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"
git remote set-url origin "https://$GITHUB_TOKEN@github.com/savas-web/linkedin-agent-2.git"

git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

echo "$(date): Update found, pulling..."
git pull origin main --quiet

# Sync shared config into .env (preserves ANTHROPIC_API_KEY)
if [ -f "$AGENT_DIR/shared_config.sh" ] && [ -f "$ENV_FILE" ]; then
    source "$AGENT_DIR/shared_config.sh"
    sed -i '' "s|^DASHBOARD_URL=.*|DASHBOARD_URL=$DASHBOARD_URL|" "$ENV_FILE"
    sed -i '' "s|^DASHBOARD_API_KEY=.*|DASHBOARD_API_KEY=$DASHBOARD_API_KEY|" "$ENV_FILE"
fi

echo "$(date): Restarting agent for $CLIENT_NAME..."
launchctl bootout gui/$(id -u) "$PLIST_PATH" 2>/dev/null || true
sleep 2
launchctl bootstrap gui/$(id -u) "$PLIST_PATH"
echo "$(date): Agent restarted."
