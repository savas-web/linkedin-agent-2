#!/bin/bash
# Installs the agent as a Mac login item via launchd

PLIST="$HOME/Library/LaunchAgents/com.rooneydigital.linkedin-agent.plist"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rooneydigital.linkedin-agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/savassuner/CLAUDE CODE/linkedin-agent/start.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/savassuner/CLAUDE CODE/linkedin-agent</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/savassuner/CLAUDE CODE/linkedin-agent/agent.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/savassuner/CLAUDE CODE/linkedin-agent/agent.log</string>
</dict>
</plist>
EOF

chmod +x "/Users/savassuner/CLAUDE CODE/linkedin-agent/start.sh"
launchctl load "$PLIST"
echo "✅ Auto-start installed. Agent will run every time you log in."
echo "   Logs: /Users/savassuner/CLAUDE CODE/linkedin-agent/agent.log"
echo ""
echo "To uninstall: launchctl unload $PLIST && rm $PLIST"
