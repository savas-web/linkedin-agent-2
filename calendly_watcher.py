import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import TELEGRAM_CHAT_ID, AGENT_NAME
import anthropic

CALENDLY_TOKEN = os.environ.get("CALENDLY_API_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {CALENDLY_TOKEN}", "Content-Type": "application/json"}
LAST_SEEN_FILE = Path("calendly_last_seen.json")
POLL_INTERVAL = 36000  # check every 10 hours
TARGET_EVENT = "Initial Flight Review"


def load_last_seen() -> str:
    if LAST_SEEN_FILE.exists():
        with open(LAST_SEEN_FILE) as f:
            return json.load(f).get("last_seen", "")
    return ""


def save_last_seen(event_uri: str):
    with open(LAST_SEEN_FILE, "w") as f:
        json.dump({"last_seen": event_uri}, f)


async def get_user_uri() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.calendly.com/users/me", headers=HEADERS)
        r.raise_for_status()
        return r.json()["resource"]["uri"]


async def get_recent_events(user_uri: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.calendly.com/scheduled_events",
            headers=HEADERS,
            params={
                "user": user_uri,
                "count": 10,
                "sort": "start_time:desc",
                "status": "active",
            }
        )
        r.raise_for_status()
        return r.json().get("collection", [])


async def get_invitee(event_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        event_id = event_uri.split("/")[-1]
        r = await client.get(
            f"https://api.calendly.com/scheduled_events/{event_id}/invitees",
            headers=HEADERS
        )
        r.raise_for_status()
        invitees = r.json().get("collection", [])
        return invitees[0] if invitees else {}


def find_linkedin_convo(name: str) -> dict:
    """Try to match the booking name to a stored LinkedIn conversation."""
    convo_log_path = Path("conversations_log.json")
    if not convo_log_path.exists():
        return {}
    with open(convo_log_path) as f:
        log = json.load(f)
    name_lower = name.lower()
    for entry in log.values():
        if name_lower in entry.get("name", "").lower():
            return entry
    return {}


def summarise_conversation(name: str, messages: list[dict]) -> str:
    if not messages:
        return "No conversation history found."
    client = anthropic.Anthropic()
    convo_text = "\n".join(
        f"{'Max' if m['role'] == 'assistant' else name}: {m['content']}"
        for m in messages
        if not m.get("is_media")
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=(
            "You summarise LinkedIn sales conversations in 4 to 6 bullet points. "
            "Cover: who they are, what they do, their main challenge or goal, "
            "key things they mentioned personally, and what stage the conversation reached. "
            "Be concise and factual. No fluff."
        ),
        messages=[{"role": "user", "content": f"Summarise this conversation:\n\n{convo_text}"}]
    )
    return response.content[0].text.strip()


async def notify_telegram(tg_app, name: str, event: dict, invitee: dict, convo: dict, browser=None):
    start = event.get("start_time", "")
    event_name = event.get("name", "Call")

    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        start_fmt = dt.strftime("%A %d %B at %H:%M UTC")
    except Exception:
        start_fmt = start

    # If no convo in log, try to find it live on LinkedIn
    if not convo and browser:
        print(f"  🔍 No log entry for {name} — searching LinkedIn messaging...")
        convo = await browser.find_conversation_by_name(name)
        if convo:
            print(f"  ✅ Found conversation for {name} on LinkedIn")

    profile_url = convo.get("profile_url", "")
    messages = convo.get("messages", [])

    # Fallback: LinkedIn search URL by name
    if not profile_url:
        search_name = name.replace(" ", "%20")
        profile_url = f"https://www.linkedin.com/search/results/people/?keywords={search_name}"
        profile_line = f"🔍 [Search LinkedIn]({profile_url})"
    else:
        profile_line = f"[View Profile]({profile_url})"

    if messages:
        summary = summarise_conversation(name, messages)
    else:
        summary = "No conversation found in agent history yet."

    text = (
        f"📅 *New Booking!*\n"
        f"🎖 {AGENT_NAME}\n\n"
        f"*Name:* {name}\n"
        f"*Call:* {event_name}\n"
        f"*Time:* {start_fmt}\n"
        f"*Email:* {invitee.get('email', 'N/A')}\n\n"
        f"*LinkedIn:* {profile_line}\n\n"
        f"*Conversation summary:*\n{summary}"
    )

    await tg_app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="Markdown"
    )


async def watch_calendly(tg_app, browser=None):
    if not CALENDLY_TOKEN:
        print("⚠️  CALENDLY_API_TOKEN not set — booking notifications disabled.")
        return

    try:
        user_uri = await get_user_uri()
        print("✅ Calendly watcher running.")
    except Exception as e:
        print(f"⚠️  Calendly auth failed: {e}")
        return

    last_seen = load_last_seen()

    while True:
        try:
            events = await get_recent_events(user_uri)
            new_events = []

            for event in events:
                uri = event.get("uri", "")
                if uri == last_seen:
                    break
                new_events.append(event)

            if new_events:
                save_last_seen(new_events[0]["uri"])

            for event in reversed(new_events):
                try:
                    if TARGET_EVENT.lower() not in event.get("name", "").lower():
                        continue
                    invitee = await get_invitee(event["uri"])
                    name = invitee.get("name", "Unknown")
                    print(f"  📅 New booking: {name}")
                    convo = find_linkedin_convo(name)
                    await notify_telegram(tg_app, name, event, invitee, convo, browser)
                except Exception as e:
                    print(f"⚠️  Error processing booking: {e}")

        except Exception as e:
            print(f"⚠️  Calendly poll error: {e}")

        await asyncio.sleep(POLL_INTERVAL)
