from fpdf import FPDF

ACCENT = (30, 90, 200)
LIGHT = (240, 244, 255)
DARK = (20, 20, 40)
GREY = (110, 110, 130)
LM = 15
RM = 15


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_margins(LM, 22, RM)
        self.set_auto_page_break(auto=True, margin=16)

    def header(self):
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, 210, 14, "F")
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.set_xy(LM, 3)
        self.cell(90, 8, "Rooney Digital - Client Onboarding Guide")
        self.set_xy(105, 3)
        self.cell(90, 8, "INTERNAL USE ONLY", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, f"Page {self.page_no()} - Rooney Digital Confidential", align="C")

    def section(self, number, title):
        self.ln(3)
        self.set_fill_color(*ACCENT)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, f"  {number}  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*DARK)
        self.ln(2)

    def step(self, label, text):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*ACCENT)
        self.set_x(LM)
        self.cell(8, 7, f"{label}.")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def note(self, text):
        self.set_fill_color(*LIGHT)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*GREY)
        self.set_x(LM)
        self.multi_cell(0, 6, f"  Note: {text}", fill=True)
        self.ln(2)
        self.set_text_color(*DARK)

    def code(self, text):
        self.set_fill_color(30, 30, 50)
        self.set_text_color(160, 210, 255)
        self.set_font("Courier", "", 9)
        self.set_x(LM)
        self.multi_cell(0, 6, f"  {text}", fill=True)
        self.set_text_color(*DARK)
        self.ln(1)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.set_x(LM + 3)
        self.multi_cell(0, 6, f"> {text}")
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.set_x(LM)
        self.multi_cell(0, 6, text)
        self.ln(2)


pdf = PDF()
pdf.add_page()

# Title
pdf.set_font("Helvetica", "B", 20)
pdf.set_text_color(*ACCENT)
pdf.ln(2)
pdf.cell(0, 12, "Client Onboarding Guide", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(*GREY)
pdf.cell(0, 7, "LinkedIn Appointment Setter - Installation Playbook", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)

pdf.body(
    "This guide walks you through installing the LinkedIn Agent on a new client's Mac "
    "via screen share. Estimated time: 15 to 20 minutes. You will need the client to "
    "have their Mac on, screen sharing active, and LinkedIn open in their browser."
)

# Section 1
pdf.section("01", "Before You Start - What You Need")
pdf.bullet("Client's Mac running macOS 12 or later")
pdf.bullet("Screen share active (Zoom, Google Meet, or FaceTime)")
pdf.bullet("Client's LinkedIn logged into their browser")
pdf.bullet("Telegram group already created for this client")
pdf.bullet("Telegram bot token for this client (created via @BotFather)")
pdf.bullet("Telegram group chat ID (get it from @userinfobot)")
pdf.bullet("Client's Calendly booking link")
pdf.bullet("A unique dashboard token you choose (e.g. smithco-2026)")
pdf.ln(1)

# Section 2
pdf.section("02", "Install Homebrew and Python")
pdf.note("Ask the client to open Terminal. Spotlight (Cmd+Space) > type Terminal > Enter.")
pdf.step("1", "Install Homebrew (safe to run even if already installed):")
pdf.code('/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
pdf.step("2", "Install Python 3:")
pdf.code("brew install python")
pdf.step("3", "Verify it works:")
pdf.code("python3 --version")
pdf.note("Should print Python 3.x.x. If so, proceed.")

# Section 3
pdf.section("03", "Get the Agent Code onto Their Mac")
pdf.step("1", "Navigate to the Desktop:")
pdf.code("cd ~/Desktop")
pdf.step("2", "Transfer the linkedin-agent-2 folder via AirDrop, Google Drive, or zip download.")
pdf.step("3", "Enter the folder:")
pdf.code("cd linkedin-agent-2")

# Section 4
pdf.section("04", "Set Up the Python Environment")
pdf.step("1", "Create the virtual environment:")
pdf.code("python3 -m venv venv")
pdf.step("2", "Activate it:")
pdf.code("source venv/bin/activate")
pdf.step("3", "Install dependencies:")
pdf.code("pip install -r requirements.txt")
pdf.step("4", "Install the Playwright browser:")
pdf.code("playwright install chromium")
pdf.note("This downloads the Chromium browser. Takes 1 to 2 minutes.")

# Section 5
pdf.section("05", "Create the Client Config")
pdf.step("1", "Run the installer to create the client folder (use a slug with no spaces):")
pdf.code("bash install_client.sh client_name")
pdf.note("The script creates the folder, asks you to fill in config.json, then exits.")
pdf.step("2", "Open config.json in TextEdit and fill in:")
pdf.bullet("agent_name: LinkedIn Agent")
pdf.bullet("telegram_bot_token: the bot token from @BotFather")
pdf.bullet("telegram_chat_id: the group chat ID (negative number from @userinfobot)")
pdf.bullet("calendly_link: the client's booking page URL")
pdf.bullet("dashboard_token: the unique token you chose")
pdf.ln(1)
pdf.step("3", "Open system_prompt.txt and personalise for this client:")
pdf.bullet("Replace [CLIENT NAME] with their full name")
pdf.bullet("Replace [BUSINESS NAME] with their company name")
pdf.bullet("Replace [BUSINESS DESCRIPTION] with a one line summary of what they do")
pdf.bullet("Update the Calendly link at the bottom of the file")

# Section 6
pdf.section("06", "Add API Keys")
pdf.step("1", "Create the .env file:")
pdf.code("nano .env")
pdf.step("2", "Paste the following, then save with Ctrl+X, Y, Enter:")
pdf.code("ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY")
pdf.code("DASHBOARD_URL=https://rooney-control-tower.up.railway.app")
pdf.code("DASHBOARD_API_KEY=rd-secret-2026")
pdf.note("The Dashboard URL and API key never change. Only the Anthropic key is yours.")

# Section 7
pdf.section("07", "Install and Start the Agent")
pdf.step("1", "Run the installer again with the client name:")
pdf.code("bash install_client.sh client_name")
pdf.step("2", "A Chromium browser window will open automatically.")
pdf.step("3", "If LinkedIn is not logged in, the client logs in with their credentials now.")
pdf.note("The browser may appear briefly and then go to the background. This is normal.")
pdf.step("4", "The agent is now running. You can close the terminal.")

# Section 8
pdf.section("08", "Verify Everything Is Working")
pdf.step("1", "Check the agent log:")
pdf.code("tail -f clients/client_name/agent.log")
pdf.note("You should see: Telegram bot running > LinkedIn browser ready > Tick")
pdf.step("2", "Check the dashboard and confirm the client appears as Online.")
pdf.step("3", "Send a message in the client Telegram group to confirm the bot responds.")

# Section 9
pdf.section("09", "Handoff Instructions for the Client")
pdf.bullet("Keep the Mac on and plugged in at all times")
pdf.bullet("Go to System Settings > Battery > Options > turn on Prevent automatic sleeping")
pdf.bullet("The agent runs in the background. No terminal or app needs to be open")
pdf.bullet("Approvals arrive in their Telegram group. Tap Approve, Edit, or Skip")
pdf.bullet("Their dashboard token lets them log in and see their stats")

# Section 10
pdf.section("10", "Troubleshooting Commands")
pdf.step("View logs", "tail -f ~/Desktop/linkedin-agent-2/clients/CLIENT_NAME/agent.log")
pdf.step("Restart agent", "launchctl unload ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist && launchctl load ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist")
pdf.step("Stop agent", "launchctl unload ~/Library/LaunchAgents/digital.rooney.CLIENT_NAME.plist")
pdf.step("Fix browser lock", "rm -f ~/Desktop/linkedin-agent-2/clients/CLIENT_NAME/linkedin_profile/SingletonLock")
pdf.note("After fixing the browser lock, restart the agent using the restart command above.")

pdf.output("Client_Onboarding_Guide.pdf")
print("PDF created: Client_Onboarding_Guide.pdf")
