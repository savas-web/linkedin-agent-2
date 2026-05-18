from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT
import sys
import os

CLIENT = sys.argv[1] if len(sys.argv) > 1 else "{CLIENT}"
OUTPUT = f"clients/{CLIENT}/Setup_Guide.pdf"
DISPLAY_NAME = " ".join(word.capitalize() for word in CLIENT.split("_"))

# Read Anthropic key from local .env
_ANTHROPIC_KEY = "YOUR_ANTHROPIC_KEY_HERE"
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        if _line.startswith("ANTHROPIC_API_KEY="):
            _ANTHROPIC_KEY = _line.strip().split("=", 1)[1]
            break

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    leftMargin=20*mm,
    rightMargin=20*mm,
    topMargin=20*mm,
    bottomMargin=20*mm,
)

styles = getSampleStyleSheet()

title_style    = ParagraphStyle("title",    fontSize=22, fontName="Helvetica-Bold",    spaceAfter=12, textColor=colors.HexColor("#0a66c2"))
subtitle_style = ParagraphStyle("subtitle", fontSize=12, fontName="Helvetica",         spaceBefore=4, spaceAfter=16, textColor=colors.HexColor("#555555"))
h2_style       = ParagraphStyle("h2",       fontSize=14, fontName="Helvetica-Bold",    spaceBefore=16, spaceAfter=6, textColor=colors.HexColor("#0a66c2"))
body_style     = ParagraphStyle("body",     fontSize=11, fontName="Helvetica",         spaceAfter=6, leading=16)
code_style     = ParagraphStyle("code",     fontSize=7.5, fontName="Courier",          spaceAfter=8, spaceBefore=4,
                                            backColor=colors.HexColor("#f4f4f4"),
                                            leftIndent=8, rightIndent=8, borderPadding=6,
                                            leading=12, wordWrap="CJK")
note_style     = ParagraphStyle("note",     fontSize=10, fontName="Helvetica-Oblique", textColor=colors.HexColor("#777777"), spaceAfter=6)
label_style    = ParagraphStyle("label",    fontSize=10, fontName="Helvetica-Bold",    spaceAfter=2)


def code_para(text: str) -> Paragraph:
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(escaped, code_style)


SETUP_CMD = f"curl -sSL https://raw.githubusercontent.com/savas-web/linkedin-agent-2/main/setup.sh -o /tmp/setup.sh && bash /tmp/setup.sh {CLIENT} {_ANTHROPIC_KEY}"

story = []

story.append(Paragraph("LinkedIn Agent", title_style))
story.append(Spacer(1, 8))
story.append(Paragraph(f"Setup Guide  |  {DISPLAY_NAME}", subtitle_style))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0a66c2"), spaceAfter=16))

steps = [
    {
        "title": "Step 1 &mdash; Open Terminal",
        "body": [
            "Press <b>Cmd + Space</b> on your keyboard to open Spotlight Search.",
            "Type <b>Terminal</b> and press Enter.",
            "A window with a blinking cursor will open. Leave it open for the whole setup.",
        ],
        "code": None,
        "note": None,
    },
    {
        "title": "Step 2 &mdash; Run the setup command",
        "body": [
            "Copy and paste the entire line below into Terminal and press Enter.",
            "This installs everything automatically: Homebrew, Python, the agent, and the browser. It takes 3 to 5 minutes. Text will scroll on the screen &mdash; that is normal. Wait until it stops completely.",
        ],
        "code": SETUP_CMD,
        "note": "If it asks for your Mac password, type it and press Enter. You will not see the password as you type &mdash; that is normal.",
    },
    {
        "title": "Step 3 &mdash; Add your two config files",
        "body": [
            "You will have received two files from your account manager:",
            "<b>config.json</b> and <b>system_prompt.txt</b>",
            "Place both files into this folder on your Mac:",
            f"Home folder &rarr; linkedin-agent-2 &rarr; clients &rarr; {CLIENT}",
            f"To get there: open Finder, click on your name in the left sidebar, open linkedin-agent-2, open clients, open {CLIENT}, then drag both files in.",
        ],
        "code": None,
        "note": None,
    },
    {
        "title": "Step 4 &mdash; Finish the installation",
        "body": [
            "Go back to Terminal and paste this in, then press Enter:",
        ],
        "code": f"cd ~/linkedin-agent-2 && bash install_client.sh {CLIENT} && bash install_updater.sh {CLIENT}",
        "note": 'Wait for it to finish. When you see "Agent installed and running" you are good.',
    },
    {
        "title": "Step 5 &mdash; Log into LinkedIn",
        "body": [
            "A Chrome window will open automatically.",
            "Log into LinkedIn as you normally would using your email and password.",
            "Once logged in, you do not need to do anything else. Minimise the window and leave it running.",
        ],
        "code": None,
        "note": None,
    },
    {
        "title": "Step 6 &mdash; Check Telegram",
        "body": [
            "Open the Telegram group your account manager added you to.",
            "Within a few minutes you will see the first approval notification appear.",
            "Tap <b>Approve</b> to send the message, <b>Edit</b> to change it before sending, or <b>Skip</b> to ignore it.",
        ],
        "code": None,
        "note": None,
    },
]

for step in steps:
    story.append(Paragraph(step["title"], h2_style))
    for line in step["body"]:
        story.append(Paragraph(line, body_style))
    if step["code"]:
        story.append(code_para(step["code"]))
    if step["note"]:
        story.append(Paragraph(f"&#128161; {step['note']}", note_style))
    story.append(Spacer(1, 4))

story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"), spaceBefore=16, spaceAfter=12))
story.append(Paragraph("You are done", h2_style))
story.append(Paragraph("The agent is now running in the background. You do not need to keep Terminal open. Your Mac just needs to be on and connected to the internet.", body_style))

story.append(Spacer(1, 8))
story.append(Paragraph("Quick reference", h2_style))

quick = [
    ("Start the agent manually",
     f"cd ~/linkedin-agent-2 && source venv/bin/activate && python main.py {CLIENT}"),
    ("Stop the agent",
     f"launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.{CLIENT}.plist"),
    ("Restart the agent",
     f"launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.{CLIENT}.plist && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/digital.rooney.{CLIENT}.plist"),
]

for label, cmd in quick:
    story.append(Paragraph(label, label_style))
    story.append(code_para(cmd))

story.append(Spacer(1, 8))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd"), spaceAfter=8))
story.append(Paragraph("Something not working? Send a screenshot of Terminal to your account manager.", note_style))

doc.build(story)
print(f"PDF saved to {OUTPUT}")
