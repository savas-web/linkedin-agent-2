# Per-Client Support Bot Deployment

Each client gets their own dedicated support bot instance. When they message it, the bot automatically knows who they are and can access their agent status.

## Setup Steps for Each Client

### 1. Create Telegram Bot via BotFather

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Choose a name (e.g. "Max Rooney Agent Support")
4. Choose a username (e.g. @max_rooney_support)
5. Copy the bot token (format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Deploy to Railway

For each client:

1. Go to [railway.app](https://railway.app) → New Project
2. Deploy from GitHub → select `savas-web/linkedin-agent-2`
3. Once created:
   - Go to Settings → Root Directory → set to `support_bot`
   - Go to Variables and add:

| Key | Value |
|-----|-------|
| `SUPPORT_BOT_TOKEN` | Bot token from step 1 |
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` (shared) |
| `CLIENT_NAME` | e.g. `max_rooney` |
| `DASHBOARD_TOKEN` | From client's config.json (e.g. `rooney-2026`) |
| `DASHBOARD_URL` | `https://rooney-control-tower.up.railway.app` |
| `DASHBOARD_API_KEY` | `rd-secret-2026` |

4. Railway deploys automatically

### 3. Share Bot Link with Client

Send them: `https://t.me/<bot_username>` (e.g. `https://t.me/max_rooney_support`)

They message the bot with questions or screenshots — no registration needed.

## Clients to Deploy

- akash_arora (needs: bot token, dashboard_token from config)
- dada_ra
- marc_miller
- max_rooney
- nuno_fontoura
- savas_suner
- shaik_wahab

## Client Experience

When they open the bot:
- Message: "Is my agent running?" → bot fetches live status and answers
- Send: Screenshot of terminal error → Claude diagnoses and suggests fix
- Send: Photo of log → Claude reads and interprets it
- Command: `/status` → see live agent status

No `/start` registration, no "who are you?" — they just use their pre-configured bot.
