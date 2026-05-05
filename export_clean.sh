#!/bin/bash
# Usage:
#   bash export_clean.sh              — generic zip with blank template
#   bash export_clean.sh dada_ra      — client zip with pre-filled config

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENT_NAME="$1"
TMP_DIR=$(mktemp -d)
DEST="$TMP_DIR/linkedin-agent-2"

mkdir -p "$DEST/clients/template"

# Core agent files
cp "$AGENT_DIR/main.py"             "$DEST/"
cp "$AGENT_DIR/linkedin_browser.py" "$DEST/"
cp "$AGENT_DIR/claude_agent.py"     "$DEST/"
cp "$AGENT_DIR/config.py"           "$DEST/"
cp "$AGENT_DIR/state.py"            "$DEST/"
cp "$AGENT_DIR/examples.py"         "$DEST/"
cp "$AGENT_DIR/telegram_bot.py"     "$DEST/"
cp "$AGENT_DIR/requirements.txt"    "$DEST/"
cp "$AGENT_DIR/install_client.sh"   "$DEST/"
cp "$AGENT_DIR/analytics.py"        "$DEST/"

# Template folder
cp "$AGENT_DIR/clients/template/config.json"       "$DEST/clients/template/"
cp "$AGENT_DIR/clients/template/system_prompt.txt" "$DEST/clients/template/"

if [ -n "$CLIENT_NAME" ]; then
    CLIENT_DIR="$AGENT_DIR/clients/$CLIENT_NAME"

    if [ ! -d "$CLIENT_DIR" ]; then
        echo "Error: No client folder found for '$CLIENT_NAME'"
        echo "Run: bash install_client.sh $CLIENT_NAME first"
        rm -rf "$TMP_DIR"
        exit 1
    fi

    mkdir -p "$DEST/clients/$CLIENT_NAME"
    cp "$CLIENT_DIR/config.json"       "$DEST/clients/$CLIENT_NAME/"
    cp "$CLIENT_DIR/system_prompt.txt" "$DEST/clients/$CLIENT_NAME/"

    OUTPUT="$HOME/Desktop/linkedin-agent-2-$CLIENT_NAME.zip"
    echo ""
    echo "Bundling pre-filled config for: $CLIENT_NAME"
else
    OUTPUT="$HOME/Desktop/linkedin-agent-2-clean.zip"
fi

rm -f "$OUTPUT"
cd "$TMP_DIR"
zip -r "$OUTPUT" linkedin-agent-2 -x "*/.DS_Store"
rm -rf "$TMP_DIR"

echo "Zip saved to: $OUTPUT"
echo "Ready to send."
