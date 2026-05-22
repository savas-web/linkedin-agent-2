# Client Onboarding Guide

## What you need before starting

- Client's full name and a slug (e.g. `jane_doe`)
- Their Telegram bot token (from @BotFather)
- Their Telegram group chat IDs (one for approvals, one for billing)
- Their Calendly or booking link
- A dashboard token you choose for them (e.g. `janedoe-2026`)
- Their next payment date

---

## Step 1 — Create the client folder on your Mac

Run this from the `linkedin-agent-2` directory:

```
bash install_client.sh CLIENT_NAME
```

Example:
```
bash install_client.sh jane_doe
```

---

## Step 2 — Fill in their config.json

Open the file:
```
open -e clients/jane_doe/config.json
```

Fill in every field:

```json
{
  "agent_name": "LinkedIn Agent",
  "telegram_bot_token": "BOT_TOKEN_FROM_BOTFATHER",
  "telegram_chat_id": -1234567890,
  "billing_chat_id": -1234567891,
  "calendly_link": "https://calendly.com/their-link",
  "calendly_api_token": "",
  "auto_threshold": 999999,
  "poll_interval": 300,
  "claude_model": "claude-sonnet-4-6",
  "dashboard_token": "janedoe-2026"
}
```

Save and close.

---

## Step 3 — Write their system_prompt.txt

Open the file:
```
open -e clients/jane_doe/system_prompt.txt
```

Write a personalised prompt for this client. Describe who they are, their offer, their ideal client, and their tone. The more specific the better.

Save and close.

---

## Step 4 — Add them to billing

Open `billing/clients.json` and add their entry:

```json
"jane_doe": {
  "name": "Jane",
  "next_payment": "2026-06-01"
}
```

---

## Step 5 — Send the client three things

Send all three via Telegram DM, Drive, or email:

**1. Their setup command** (swap in their slug):
```
curl -sSL https://raw.githubusercontent.com/savas-web/linkedin-agent-2/main/setup.sh | bash -s jane_doe sk-ant-api03-YOUR_KEY_HERE
```

**2. Their config.json** — from `clients/jane_doe/config.json`

**3. Their system_prompt.txt** — from `clients/jane_doe/system_prompt.txt`

**4. Their Setup_Guide.pdf** — generated from `generate_setup_pdf.py`

---

## Step 6 — Client runs the setup command

**Important:** If Homebrew is not installed on their Mac, they must install it first:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then they run the setup command. It downloads the agent, installs dependencies, and sets up auto-updates.

---

## Step 7 — Client adds their two files

They place `config.json` and `system_prompt.txt` into:
```
~/linkedin-agent-2/clients/jane_doe/
```

Then run:
```
cd ~/linkedin-agent-2 && bash install_client.sh jane_doe && bash install_updater.sh jane_doe
```

---

## Step 8 — Client logs into LinkedIn

A Chrome window opens automatically. They log into LinkedIn as normal. The session is saved and they never need to log in again.

---

## Step 9 — Confirm it is working

Ask the client to send you a screenshot of their Telegram approval group — they should see the first notification within 5 minutes.

---

## Pushing updates to all clients

Any code change you make reaches every client within 1 hour automatically. Just:

```
git add .
git commit -m "describe the change"
git push
```

---

## Dashboard login tokens

| Client | Token |
|---|---|
| Max Rooney | `rooney-2026` |
| Dada Ra | `dadara-2026` |
| Shaik Wahab | `wahab-2026` |
| Akash Arora | `akash-2026` |
| Marc Miller | `marc-2026` |

---

## Generating a setup PDF for a new client

```
cd linkedin-agent-2
source venv/bin/activate
python generate_setup_pdf.py CLIENT_NAME
```

PDF saves to `clients/CLIENT_NAME/Setup_Guide.pdf` and should be copied to the Control tower clients onboarding folder on Desktop.
