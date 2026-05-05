#!/bin/bash
CLIENT_NAME="$1"
AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$CLIENT_NAME" ]; then
    echo "Usage: bash install_updater.sh <client_name>"
    exit 1
fi

PLIST_LABEL="digital.rooney.$CLIENT_NAME.updater"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
LOG_FILE="$AGENT_DIR/clients/$CLIENT_NAME/updater.log"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$AGENT_DIR/auto_update.sh</string>
        <string>$CLIENT_NAME</string>
    </array>

    <key>WorkingDirectory</key>
    <string>$AGENT_DIR</string>

    <key>StartInterval</key>
    <integer>3600</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$LOG_FILE</string>

    <key>StandardErrorPath</key>
    <string>$LOG_FILE</string>
</dict>
</plist>
EOF

launchctl bootout gui/$(id -u) "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST_PATH"

echo "Auto-updater installed for $CLIENT_NAME. Checks for updates every hour."
