import json
import httpx

TOKEN = "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"
PARENT_ID = "3508845b-d58d-8061-843f-fcb0ee4fb647"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def heading(text, level=2):
    tag = f"heading_{level}"
    return {"object": "block", "type": tag, tag: {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def para(text, bold=False):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}, "annotations": {"bold": bold}}]}}


def code(text):
    return {"object": "block", "type": "code", "code": {"language": "shell", "rich_text": [{"type": "text", "text": {"content": text}}]}}


def callout(text, emoji="📝"):
    return {"object": "block", "type": "callout", "callout": {"icon": {"type": "emoji", "emoji": emoji}, "rich_text": [{"type": "text", "text": {"content": text}}]}}


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


def bullet(text):
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def numbered(text):
    return {"object": "block", "type": "numbered_list_item", "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


blocks = [
    callout("This is an internal guide for Rooney Digital team. Follow each section in order while screen sharing with the client. Estimated time: 15 to 20 minutes.", "🎖"),
    divider(),

    heading("01  Before You Start", 2),
    para("Make sure you have the following ready before the call:"),
    bullet("Client's Mac running macOS 12 or later"),
    bullet("Screen share active (Zoom, Google Meet, or FaceTime)"),
    bullet("Client's LinkedIn logged in on their browser"),
    bullet("Telegram group already created for this client"),
    bullet("Telegram bot token from @BotFather"),
    bullet("Telegram group chat ID from @userinfobot (negative number)"),
    bullet("Client's Calendly booking link"),
    bullet("A unique dashboard token you choose, e.g. smithco-2026"),
    divider(),

    heading("02  Open Terminal", 2),
    callout("Ask the client to press Cmd + Space, type Terminal, and press Enter.", "💻"),
    divider(),

    heading("03  Install Homebrew and Python", 2),
    para("Step 1. Install Homebrew (safe to run even if already installed):"),
    code('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'),
    para("Step 2. Install Python 3:"),
    code("brew install python"),
    para("Step 3. Confirm it works:"),
    code("python3 --version"),
    callout("Should print Python 3.x.x. If so, move on.", "✅"),
    divider(),

    heading("04  Get the Agent Code onto Their Mac", 2),
    para("Step 1. Navigate to the Desktop:"),
    code("cd ~/Desktop"),
    para("Step 2. Transfer the linkedin-agent-2 folder via AirDrop, Google Drive, or a zip download."),
    para("Step 3. Enter the folder:"),
    code("cd linkedin-agent-2"),
    divider(),

    heading("05  Set Up the Python Environment", 2),
    para("Step 1. Create the virtual environment:"),
    code("python3 -m venv venv"),
    para("Step 2. Activate it:"),
    code("source venv/bin/activate"),
    para("Step 3. Install dependencies:"),
    code("pip install -r requirements.txt"),
    para("Step 4. Install the Playwright browser (takes 1 to 2 minutes):"),
    code("playwright install chromium"),
    divider(),

    heading("06  Create the Client Config", 2),
    para("Step 1. Run the installer to generate the client folder:"),
    code("bash install_client.sh client_name"),
    callout("Replace client_name with a lowercase slug, no spaces. Example: john_smith", "📝"),
    para("The script creates the folder and exits. Now fill in the files."),
    para("Step 2. Open clients/client_name/config.json and fill in:"),
    bullet("agent_name: LinkedIn Agent"),
    bullet("telegram_bot_token: the bot token from @BotFather"),
    bullet("telegram_chat_id: the group chat ID (negative number)"),
    bullet("calendly_link: the client's booking page URL"),
    bullet("dashboard_token: the unique token you chose"),
    para("Step 3. Open clients/client_name/system_prompt.txt and personalise:"),
    bullet("Replace [CLIENT NAME] with their full name"),
    bullet("Replace [BUSINESS NAME] with their company name"),
    bullet("Replace [BUSINESS DESCRIPTION] with one line on what they do"),
    bullet("Update the Calendly link at the bottom"),
    divider(),

    heading("07  Add API Keys", 2),
    para("Step 1. Create the .env file:"),
    code("nano .env"),
    para("Step 2. Paste the following three lines, then press Ctrl+X, Y, Enter to save:"),
    code("ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY\nDASHBOARD_URL=https://rooney-control-tower.up.railway.app\nDASHBOARD_API_KEY=rd-secret-2026"),
    callout("The Dashboard URL and API key never change. Only swap in your Anthropic key.", "🔑"),
    divider(),

    heading("08  Install and Start the Agent", 2),
    para("Run the installer again with the same client name:"),
    code("bash install_client.sh client_name"),
    para("A Chromium browser window will open. If LinkedIn is not logged in, the client logs in now with their credentials."),
    callout("The browser may appear briefly then go to the background. This is normal. The agent is running.", "✅"),
    divider(),

    heading("09  Verify Everything Is Working", 2),
    para("Step 1. Check the agent log:"),
    code("tail -f clients/client_name/agent.log"),
    callout("You should see: Telegram bot running > LinkedIn browser ready > Tick", "✅"),
    para("Step 2. Open the dashboard and confirm the client appears as Online."),
    para("Step 3. Send a test message in the Telegram group to confirm the bot is active."),
    divider(),

    heading("10  Handoff to Client", 2),
    bullet("Tell them to keep the Mac on and plugged in"),
    bullet("System Settings > Battery > Options > turn on Prevent automatic sleeping"),
    bullet("The agent runs in the background. No terminal or app needs to stay open"),
    bullet("Approvals arrive in Telegram. They tap Approve, Edit, or Skip"),
    bullet("Give them their dashboard token to log in and see their stats"),
    divider(),

    heading("11  Troubleshooting Commands", 2),
    para("View live logs:"),
    code("tail -f ~/Desktop/linkedin-agent-2/clients/CLIENT_NAME/agent.log"),
    para("Restart the agent:"),
    code("launchctl unload ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist && launchctl load ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist"),
    para("Stop the agent:"),
    code("launchctl unload ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist"),
    para("Fix browser lock error:"),
    code("rm -f ~/Desktop/linkedin-agent-2/clients/CLIENT_NAME/linkedin_profile/SingletonLock"),
    callout("After removing the lock file, restart the agent using the restart command above.", "⚠️"),
]


def create_page(blocks_chunk):
    return httpx.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json={
            "parent": {"page_id": PARENT_ID},
            "properties": {
                "title": {"title": [{"text": {"content": "Client Onboarding Guide"}}]}
            },
            "children": blocks_chunk,
        },
        timeout=30,
    )


# Notion allows max 100 blocks per request
CHUNK = 100
r = create_page(blocks[:CHUNK])
data = r.json()

if "id" not in data:
    print("Error:", data)
    exit(1)

page_id = data["id"]
page_url = data["url"]
print(f"Page created: {page_url}")

# Append remaining blocks if any
for i in range(CHUNK, len(blocks), CHUNK):
    httpx.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=HEADERS,
        json={"children": blocks[i:i+CHUNK]},
        timeout=30,
    )

print("Done.")
