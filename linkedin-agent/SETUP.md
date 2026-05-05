# LinkedIn Appointment Setter — Setup

## 1. Install dependencies

```bash
cd linkedin-agent
pip install -r requirements.txt
playwright install chromium
```

## 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Add this to your `~/.zshrc` to make it permanent.

## 3. Run the agent

```bash
python main.py
```

On first run, a Chrome window opens. **Log in to LinkedIn manually** — the session is saved to `./linkedin_profile/` so you only do this once.

## 4. Telegram approval flow

When a new unread message comes in (for the first 10), you'll get a Telegram notification like:

```
📩 New LinkedIn DM
From: John Smith

Their message:
Hey Max! Loved your post on personal branding...

Proposed reply:
Thanks John! Yeah that one really hit — what kind of coaching do you do?

[✅ Approve]  [✏️ Edit]  [⏭️ Skip]
```

- **Approve** — sends immediately
- **Edit** — bot prompts you to type a replacement, then sends
- **Skip** — ignores the message this cycle

After **10 approved/sent messages**, the agent goes fully autonomous.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Orchestration loop |
| `linkedin_browser.py` | Playwright browser automation |
| `claude_agent.py` | Claude reply generation |
| `telegram_bot.py` | Telegram approval UI |
| `state.json` | Auto-created, tracks sent count + queue |
| `linkedin_profile/` | Auto-created, stores LinkedIn session |

## Adjusting behaviour

- **Poll interval**: change `POLL_INTERVAL` in `config.py` (default 90s)
- **Auto threshold**: change `AUTO_THRESHOLD` in `config.py` (default 10)
- **Agent persona / instructions**: edit `SYSTEM_PROMPT` in `config.py`
