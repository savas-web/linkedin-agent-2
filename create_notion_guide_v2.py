import httpx

TOKEN = "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"
PARENT_ID = "3508845b-d58d-8061-843f-fcb0ee4fb647"
OLD_PAGE_ID = "3508845b-d58d-8159-95d3-ca8bd6044b34"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def h2(text):
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def h3(text):
    return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def para(text):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

def bold(text):
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}, "annotations": {"bold": True}}]}}

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
    callout("Internal guide for Rooney Digital. Follow each section in order while screen sharing with the client. Estimated time: 15 to 20 minutes.", "🎖"),
    divider(),

    # SECTION 1
    h2("01  Before You Start"),
    para("Have these ready before the screen share begins:"),
    bullet("Client's Mac on and screen share active"),
    bullet("Client's LinkedIn open and logged in on their browser"),
    bullet("Telegram group created with the bot already added"),
    bullet("Bot token from @BotFather"),
    bullet("Group chat ID from @userinfobot"),
    bullet("Client's Calendly link"),
    bullet("A unique dashboard token you choose, e.g. smithco-2026"),
    divider(),

    # SECTION 2
    h2("02  Open Terminal on Their Mac"),
    numbered("Press Cmd + Space on their keyboard to open Spotlight"),
    numbered("Type Terminal and press Enter"),
    numbered("A black or white window opens with a command prompt. This is Terminal."),
    callout("Keep Terminal open for the rest of the setup. Do not close it.", "💻"),
    divider(),

    # SECTION 3
    h2("03  Install Homebrew and Python"),
    para("Homebrew is a package manager for Mac. We need it to install Python."),
    h3("Install Homebrew"),
    para("Paste this into Terminal and press Enter:"),
    code('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'),
    callout("It will ask for their Mac password. They type it (nothing shows on screen, that is normal) and press Enter. This takes 2 to 3 minutes.", "🔑"),
    h3("Install Python"),
    para("When Homebrew is done, paste this and press Enter:"),
    code("brew install python"),
    h3("Confirm it worked"),
    code("python3 --version"),
    callout("It should print something like Python 3.13.0. If you see a version number, you are good to move on.", "✅"),
    divider(),

    # SECTION 4
    h2("04  Get the Agent Folder onto Their Mac"),
    para("You need to transfer the linkedin-agent-2 folder to their Desktop."),
    h3("Option A: AirDrop (easiest if you are nearby)"),
    numbered("On your Mac, right click the linkedin-agent-2 folder"),
    numbered("Click Share > AirDrop"),
    numbered("Select the client's Mac"),
    numbered("On their Mac, click Accept"),
    numbered("The folder downloads to their Downloads folder"),
    numbered("Drag it to the Desktop"),
    h3("Option B: Google Drive (for remote screen share)"),
    numbered("Zip the linkedin-agent-2 folder on your Mac"),
    numbered("Upload the zip to Google Drive and get a shareable link"),
    numbered("Send the link to the client"),
    numbered("They download and unzip it to their Desktop"),
    h3("Enter the folder in Terminal"),
    para("Once the folder is on their Desktop, paste this in Terminal:"),
    code("cd ~/Desktop/linkedin-agent-2"),
    callout("If they put it somewhere other than the Desktop, adjust the path. Type cd ~/Desktop/ and press Tab to autocomplete folder names.", "📝"),
    divider(),

    # SECTION 5
    h2("05  Set Up the Python Environment"),
    para("This creates an isolated Python environment just for this agent."),
    h3("Create the environment"),
    code("python3 -m venv venv"),
    callout("No output means it worked. If you see an error, check that Python installed correctly in step 03.", "✅"),
    h3("Activate the environment"),
    code("source venv/bin/activate"),
    callout("You will see (venv) appear at the start of the Terminal line. This means it is active. You must see this before continuing.", "✅"),
    h3("Install the required packages"),
    code("pip install -r requirements.txt"),
    callout("This installs all the libraries the agent needs. Takes about 1 minute. You will see a lot of output, that is normal.", "⏳"),
    h3("Install the browser"),
    code("playwright install chromium"),
    callout("This downloads a special version of Chrome that the agent uses to control LinkedIn. Takes 1 to 2 minutes.", "⏳"),
    divider(),

    # SECTION 6
    h2("06  Create the Client Folder"),
    para("This sets up the folder structure for this specific client."),
    h3("Run the installer"),
    para("Replace john_smith with the actual client slug (lowercase, no spaces):"),
    code("bash install_client.sh john_smith"),
    callout("The script will create the folder and then exit asking you to fill in the config. That is correct. Do not run it again yet.", "📝"),
    h3("Open the config file"),
    para("In Terminal, open config.json in a text editor:"),
    code("open -e clients/john_smith/config.json"),
    callout("This opens the file in TextEdit. You will see placeholder values that you need to replace.", "📝"),
    h3("Fill in config.json"),
    para("Replace each placeholder with the real values:"),
    bullet('agent_name: change to "LinkedIn Agent"'),
    bullet("telegram_bot_token: paste the bot token from @BotFather, it looks like 1234567890:ABCdef..."),
    bullet("telegram_chat_id: paste the group chat ID, it is a negative number like -1001234567890"),
    bullet("calendly_link: paste the client's full Calendly URL"),
    bullet('dashboard_token: type the unique token you chose, e.g. "smithco-2026"'),
    para("Save the file with Cmd + S and close TextEdit."),
    h3("Fill in the system prompt"),
    para("Open the system prompt file:"),
    code("open -e clients/john_smith/system_prompt.txt"),
    bullet("Replace [CLIENT NAME] with their first name, e.g. John"),
    bullet("Replace [BUSINESS NAME] with their company name"),
    bullet("Replace [BUSINESS DESCRIPTION] with one line on what they do"),
    bullet("Update the Calendly link near the bottom of the file"),
    para("Save with Cmd + S and close TextEdit."),
    divider(),

    # SECTION 7
    h2("07  Add the API Keys"),
    para("The agent needs three keys to connect to Claude AI and the dashboard."),
    h3("Create the .env file"),
    code("nano .env"),
    callout("This opens a simple text editor inside Terminal. Do not be put off by it, you just paste and save.", "📝"),
    h3("Paste the three keys"),
    para("Copy and paste these three lines (with your real Anthropic key):"),
    code("ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY_HERE\nDASHBOARD_URL=https://rooney-control-tower.up.railway.app\nDASHBOARD_API_KEY=rd-secret-2026"),
    h3("Save and close nano"),
    numbered("Press Ctrl + X"),
    numbered("Press Y to confirm saving"),
    numbered("Press Enter to keep the filename"),
    callout("You are back at the normal Terminal prompt. The .env file is saved.", "✅"),
    divider(),

    # SECTION 8
    h2("08  Install and Start the Agent"),
    para("Run the installer again with the same client name:"),
    code("bash install_client.sh john_smith"),
    callout("This time it will install the agent as a background service and start it immediately.", "🚀"),
    h3("What happens next"),
    numbered("A Chrome browser window opens automatically on their Mac"),
    numbered("If LinkedIn is not logged in, the client logs in now with their own credentials"),
    numbered("Once LinkedIn loads, the browser goes to the background"),
    numbered("The agent is now running silently in the background"),
    callout("The browser may flash open and close quickly. That is completely normal. The agent is running.", "✅"),
    divider(),

    # SECTION 9
    h2("09  Verify the Agent is Running"),
    h3("Check the live log"),
    para("Run this in Terminal to see what the agent is doing:"),
    code("tail -f clients/john_smith/agent.log"),
    para("You should see these three lines appear:"),
    bullet("Telegram bot running"),
    bullet("LinkedIn browser ready"),
    bullet("Tick (followed by No unread conversations or a list of conversations)"),
    callout("If you see all three lines, the agent is fully working. Press Ctrl + C to stop watching the log.", "✅"),
    h3("Check the dashboard"),
    numbered("Go to dashboard-rooney-digital.up.railway.app"),
    numbered("Log in with the master token"),
    numbered("The client should appear with a green Online status"),
    h3("Send a test Telegram message"),
    para("Send any message in the client's Telegram group to confirm the bot is connected and active."),
    divider(),

    # SECTION 10
    h2("10  Handoff to the Client"),
    para("Before you end the screen share, do these things:"),
    h3("Prevent the Mac from sleeping"),
    numbered("Open System Settings on their Mac"),
    numbered("Go to Battery > Options"),
    numbered("Turn on Prevent automatic sleeping when display is off"),
    callout("This is critical. If the Mac sleeps, the agent stops. Make sure this is done before you leave.", "⚠️"),
    h3("Tell the client"),
    bullet("Keep the Mac on and plugged in at all times"),
    bullet("The agent runs in the background. No app or terminal needs to stay open"),
    bullet("Approvals will arrive in their Telegram group. They tap Approve, Edit, or Skip"),
    bullet("Give them their dashboard token so they can check their own stats"),
    divider(),

    # SECTION 11
    h2("11  Troubleshooting"),
    h3("View live logs"),
    code("tail -f ~/Desktop/linkedin-agent-2/clients/CLIENT_NAME/agent.log"),
    h3("Restart the agent"),
    code("launchctl unload ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist && launchctl load ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist"),
    h3("Stop the agent"),
    code("launchctl unload ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist"),
    h3("Fix browser lock error"),
    code("rm -f ~/Desktop/linkedin-agent-2/clients/CLIENT_NAME/linkedin_profile/SingletonLock"),
    callout("After removing the lock, restart the agent using the restart command above.", "⚠️"),
]


# Archive old page
httpx.patch(
    f"https://api.notion.com/v1/pages/{OLD_PAGE_ID}",
    headers=HEADERS,
    json={"archived": True},
    timeout=10,
)
print("Old page archived.")

# Create new page
CHUNK = 100
r = httpx.post(
    "https://api.notion.com/v1/pages",
    headers=HEADERS,
    json={
        "parent": {"page_id": PARENT_ID},
        "properties": {"title": {"title": [{"text": {"content": "Client Onboarding Guide"}}]}},
        "children": blocks[:CHUNK],
    },
    timeout=30,
)
data = r.json()

if "id" not in data:
    print("Error:", data)
    exit(1)

page_id = data["id"]
print(f"Page created: {data['url']}")

for i in range(CHUNK, len(blocks), CHUNK):
    httpx.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=HEADERS,
        json={"children": blocks[i:i+CHUNK]},
        timeout=30,
    )

print("Done.")
