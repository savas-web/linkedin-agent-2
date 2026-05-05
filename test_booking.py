import asyncio
import os
import httpx
from telegram import Bot
from calendly_watcher import find_linkedin_convo, notify_telegram, summarise_conversation
from linkedin_browser import LinkedInBrowser
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TARGET_EVENT = "Initial Flight Review"

async def test():
    token = os.environ.get("CALENDLY_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        me = await client.get("https://api.calendly.com/users/me", headers=headers)
        user_uri = me.json()["resource"]["uri"]
        events_resp = await client.get(
            "https://api.calendly.com/scheduled_events",
            headers=headers,
            params={"user": user_uri, "count": 10, "sort": "start_time:desc", "status": "active"}
        )
        events = events_resp.json()["collection"]

    # Find most recent Initial Flight Review
    event = None
    for e in events:
        if TARGET_EVENT.lower() in e.get("name", "").lower():
            event = e
            break

    if not event:
        print(f"No '{TARGET_EVENT}' booking found.")
        return

    event_id = event["uri"].split("/")[-1]
    async with httpx.AsyncClient() as client:
        inv_resp = await client.get(
            f"https://api.calendly.com/scheduled_events/{event_id}/invitees",
            headers=headers
        )
        invitees = inv_resp.json()["collection"]
        invitee = invitees[0] if invitees else {}

    name = invitee.get("name", "Unknown")
    print(f"Found booking: {name} | {event['name']} | {event['start_time']}")

    convo = find_linkedin_convo(name)

    browser = LinkedInBrowser()
    await browser.start()

    async with Bot(TELEGRAM_BOT_TOKEN) as bot:
        class MockApp:
            pass
        app = MockApp()
        app.bot = bot
        await notify_telegram(app, name, event, invitee, convo, browser)
        print(f"✅ Notification sent to chat {TELEGRAM_CHAT_ID}")

    await browser.stop()

asyncio.run(test())
