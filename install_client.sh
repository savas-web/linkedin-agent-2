#!/bin/bash
set -e

CLIENT_NAME="$1"
AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENT_DIR="$AGENT_DIR/clients/$CLIENT_NAME"
VENV_PYTHON="$AGENT_DIR/venv/bin/python3"
PLIST_LABEL="digital.rooney.$CLIENT_NAME"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
LOG_FILE="$CLIENT_DIR/agent.log"
ENV_FILE="$AGENT_DIR/.env"

# ── Validation ────────────────────────────────────────────────────────────────

if [ -z "$CLIENT_NAME" ]; then
  echo "Usage: ./install_client.sh <client_name>"
  echo "Example: ./install_client.sh john_smith"
  exit 1
fi

if [ ! -f "$VENV_PYTHON" ]; then
  echo "Error: venv not found at $VENV_PYTHON"
  echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# ── Create client folder from template if new ─────────────────────────────────

if [ ! -d "$CLIENT_DIR" ]; then
  echo "Creating new client folder from template..."
  cp -r "$AGENT_DIR/clients/template" "$CLIENT_DIR"
  echo ""
  echo "Client folder created at: $CLIENT_DIR"
  echo ""
  echo "Before continuing, fill in:"
  echo "  $CLIENT_DIR/config.json   — Telegram token, chat ID, dashboard token"
  echo "  $CLIENT_DIR/system_prompt.txt — Personalise for this client"
  echo ""
  echo "Then run this script again."
  exit 0
fi

if [ ! -f "$CLIENT_DIR/config.json" ]; then
  echo "Error: $CLIENT_DIR/config.json not found."
  exit 1
fi

# ── Load env vars ─────────────────────────────────────────────────────────────

if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
DASHBOARD_URL="${DASHBOARD_URL:-}"
DASHBOARD_API_KEY="${DASHBOARD_API_KEY:-}"
OPERATOR_BOT_TOKEN="${OPERATOR_TELEGRAM_BOT_TOKEN:-}"
OPERATOR_CHAT_ID="${OPERATOR_TELEGRAM_CHAT_ID:-}"

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY not set. Add it to $ENV_FILE"
  exit 1
fi

# ── Unload existing plist if running ─────────────────────────────────────────

if [ -f "$PLIST_PATH" ]; then
  echo "Stopping existing agent for $CLIENT_NAME..."
  launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# ── Write launchd plist ───────────────────────────────────────────────────────

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$VENV_PYTHON</string>
        <string>$AGENT_DIR/main.py</string>
        <string>$CLIENT_NAME</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$AGENT_DIR</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>$ANTHROPIC_API_KEY</string>
        <key>DASHBOARD_URL</key>
        <string>$DASHBOARD_URL</string>
        <key>DASHBOARD_API_KEY</key>
        <string>$DASHBOARD_API_KEY</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>OPERATOR_TELEGRAM_BOT_TOKEN</key>
        <string>$OPERATOR_BOT_TOKEN</string>
        <key>OPERATOR_TELEGRAM_CHAT_ID</key>
        <string>$OPERATOR_CHAT_ID</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>ThrottleInterval</key>
    <integer>30</integer>

    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>

    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>
</dict>
</plist>
EOF

# ── Load it ───────────────────────────────────────────────────────────────────

launchctl load "$PLIST_PATH"

echo ""
echo "Agent installed and running for: $CLIENT_NAME"
echo ""
echo "Logs:      tail -f $LOG_FILE"
echo "Stop:      launchctl unload $PLIST_PATH"
echo "Restart:   launchctl unload $PLIST_PATH && launchctl load $PLIST_PATH"
echo "Uninstall: launchctl unload $PLIST_PATH && rm $PLIST_PATH"
