#!/bin/bash
set -e

CLIENT_NAME="$1"
REPO="https://github.com/savas-web/linkedin-agent-2.git"
INSTALL_DIR="$HOME/Desktop/linkedin-agent-2"

if [ -z "$CLIENT_NAME" ]; then
    echo "Usage: bash setup.sh <client_name>"
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
    git pull origin main --quiet
else
    echo "Downloading agent..."
    git clone "$REPO" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
fi

# Check for config files
CONFIG_FILE="$INSTALL_DIR/clients/$CLIENT_NAME/config.json"
PROMPT_FILE="$INSTALL_DIR/clients/$CLIENT_NAME/system_prompt.txt"

if [ ! -f "$CONFIG_FILE" ] || [ ! -f "$PROMPT_FILE" ]; then
    echo ""
    echo "Almost there! You need to add two files before the agent can start:"
    echo ""
    echo "  1. config.json       -> $INSTALL_DIR/clients/$CLIENT_NAME/config.json"
    echo "  2. system_prompt.txt -> $INSTALL_DIR/clients/$CLIENT_NAME/system_prompt.txt"
    echo ""
    echo "Your account manager will send these to you."
    echo "Once you have added them, run:"
    echo ""
    echo "  cd $INSTALL_DIR && bash install_client.sh $CLIENT_NAME && bash install_updater.sh $CLIENT_NAME"
    echo ""
    mkdir -p "$INSTALL_DIR/clients/$CLIENT_NAME"
    exit 0
fi

# Set up Python venv
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "Installing Python dependencies..."
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --quiet
fi

# Set up .env if missing
ENV_FILE="$INSTALL_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "One more thing — add your .env file to:"
    echo "  $ENV_FILE"
    echo ""
    echo "Your account manager will send this to you."
    exit 0
fi

# Install agent and updater
bash "$INSTALL_DIR/install_client.sh" "$CLIENT_NAME"
bash "$INSTALL_DIR/install_updater.sh" "$CLIENT_NAME"

echo ""
echo "All done! The agent is running and will auto-update whenever there is a new version."
echo ""
