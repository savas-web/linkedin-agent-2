#!/bin/bash
set -e

CLIENT_NAME="$1"
ANTHROPIC_KEY="$2"
GITHUB_TOKEN="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"
REPO="https://$GITHUB_TOKEN@github.com/savas-web/linkedin-agent-2.git"
INSTALL_DIR="$HOME/linkedin-agent-2"

if [ -z "$CLIENT_NAME" ] || [ -z "$ANTHROPIC_KEY" ]; then
    echo "Usage: bash setup.sh <client_name> <anthropic_api_key>"
    exit 1
fi

echo ""
echo "Setting up LinkedIn Agent for: $CLIENT_NAME"
echo ""

# Install Homebrew if missing
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null
fi

# Install git if missing
if ! command -v git &>/dev/null; then
    echo "Installing git..."
    brew install git
fi

# Install python if missing
if ! command -v python3 &>/dev/null; then
    echo "Installing Python..."
    brew install python
fi

# Clone or pull repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git remote set-url origin "$REPO"
    git pull origin main --quiet
else
    echo "Downloading agent..."
    git clone "$REPO" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
fi

# Write .env from shared_config + Anthropic key
source "$INSTALL_DIR/shared_config.sh"
cat > "$INSTALL_DIR/.env" <<EOF
ANTHROPIC_API_KEY=$ANTHROPIC_KEY
DASHBOARD_URL=$DASHBOARD_URL
DASHBOARD_API_KEY=$DASHBOARD_API_KEY
EOF

# Set up Python venv
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "Installing Python dependencies..."
    python3 -m venv "$INSTALL_DIR/venv"
fi

source "$INSTALL_DIR/venv/bin/activate"
pip install -r "$INSTALL_DIR/requirements.txt" --quiet

# Install Playwright browser
echo "Installing browser..."
playwright install chromium --quiet 2>/dev/null || python3 -m playwright install chromium

# Check for config files
CONFIG_FILE="$INSTALL_DIR/clients/$CLIENT_NAME/config.json"
PROMPT_FILE="$INSTALL_DIR/clients/$CLIENT_NAME/system_prompt.txt"
mkdir -p "$INSTALL_DIR/clients/$CLIENT_NAME"

if [ ! -f "$CONFIG_FILE" ] || [ ! -f "$PROMPT_FILE" ]; then
    echo ""
    echo "Almost there! Send the client their two files via Telegram:"
    echo ""
    echo "  config.json       -> $CONFIG_FILE"
    echo "  system_prompt.txt -> $PROMPT_FILE"
    echo ""
    echo "Once they are in place, run:"
    echo "  cd $INSTALL_DIR && bash install_client.sh $CLIENT_NAME && bash install_updater.sh $CLIENT_NAME"
    echo ""
    exit 0
fi

# Install agent and updater
bash "$INSTALL_DIR/install_client.sh" "$CLIENT_NAME"
bash "$INSTALL_DIR/install_updater.sh" "$CLIENT_NAME"

echo ""
echo "All done! The agent is running and will auto-update whenever there is a new version."
echo ""
