# Client Onboarding Guide

## What you need before starting

- Client's full name and a slug (e.g. `jane_doe`)
- Their Telegram bot token (from @BotFather)
- Their Telegram group chat ID
- Their Calendly or booking link
- A dashboard token you choose for them (e.g. `janedoe-2026`)

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

This creates `clients/jane_doe/` with blank template files.

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

## Step 4 — Send the client three things

Send all three via Telegram DM or email:

**1. Their setup command** (swap in their slug and the Anthropic key):
```
curl -sSL https://raw.githubusercontent.com/savas-web/linkedin-agent-2/main/setup.sh | bash -s jane_doe sk-ant-api03-YOUR_KEY_HERE
```

**2. Their config.json** — the file you just filled in at `clients/jane_doe/config.json`

**3. Their system_prompt.txt** — the file you just wrote at `clients/jane_doe/system_prompt.txt`

---

## Step 5 — Client runs the setup command

They paste the command into Terminal and hit Enter. It:
- Downloads the agent
- Installs all dependencies
- Writes their .env automatically
- Sets up auto-updates

When it finishes it will tell them where to put the two files.

---

## Step 6 — Client adds their two files

They place `config.json` and `system_prompt.txt` into:
```
~/Desktop/linkedin-agent-2/clients/jane_doe/
```

Then run:
```
cd ~/Desktop/linkedin-agent-2 && bash install_client.sh jane_doe && bash install_updater.sh jane_doe
```

---

## Step 7 — Client logs into LinkedIn

A Chrome window opens automatically. They log into LinkedIn as normal. The session is saved and they never need to log in again.

---

## Step 8 — Confirm it is working

Ask the client to send you a screenshot of their Telegram — they should see the agent's first approval notification within 5 minutes.

---

## Pushing updates to all clients

Any code change you make reaches every client within 1 hour automatically. Just:

```
git add .
git commit -m "describe the change"
git push
```

Never send a zip again.

---

## Dashboard login tokens

| Client | Token |
|---|---|
| Max Rooney | `rooney-2026` |
| Dada Ra | `dadara-2026` |

Add new clients to this table as you onboard them.
