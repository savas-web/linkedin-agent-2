import asyncio
import re
from playwright.async_api import async_playwright, BrowserContext
from config import LINKEDIN_USER_DATA_DIR


class LinkedInBrowser:
    def __init__(self):
        self.playwright = None
        self.context: BrowserContext = None
        self.page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=LINKEDIN_USER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self.context.new_page()

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()

    async def ensure_logged_in(self):
        await self.page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        if "login" in self.page.url or "authwall" in self.page.url or "checkpoint" in self.page.url:
            print("\n⚠️  Please log in to LinkedIn in the browser window.")
            print("The agent will continue once you're logged in...\n")
            await self.page.wait_for_url("**/messaging/**", timeout=180_000)
            await asyncio.sleep(3)
            print("✅ Logged in to LinkedIn!")

    async def get_unread_conversations(self) -> list[dict]:
        try:
            await self.page.goto("https://www.linkedin.com/messaging/?filter=unread", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            await self.page.wait_for_selector("li.msg-conversation-listitem", timeout=15_000)
            await asyncio.sleep(1)

            results = []
            items = await self.page.query_selector_all("li.msg-conversation-listitem")
            print(f"  Found {len(items)} unread conversations")

            for item in items:
                try:
                    link_div = await item.query_selector(".msg-conversation-listitem__link")
                    if not link_div:
                        continue
                    await link_div.click()
                    await asyncio.sleep(2)

                    url = self.page.url
                    match = re.search(r"/messaging/thread/([^/?]+)", url)
                    if not match:
                        continue
                    thread_id = match.group(1)

                    name_el = await item.query_selector(".msg-conversation-card__participant-names span")
                    name = (await name_el.inner_text()).strip() if name_el else "Unknown"

                    # Grab profile URL from the conversation header while we're here
                    profile_url = await self._get_profile_url_from_conversation()

                    results.append({"thread_id": thread_id, "name": name, "profile_url": profile_url})

                    await self.page.goto("https://www.linkedin.com/messaging/?filter=unread", wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    await self.page.wait_for_selector("li.msg-conversation-listitem", timeout=10_000)
                    items = await self.page.query_selector_all("li.msg-conversation-listitem")
                except Exception:
                    continue

            return results
        except Exception as e:
            print(f"⚠️  Error fetching conversations: {e}")
            return []

    async def _get_profile_url_from_conversation(self) -> str:
        try:
            # The conversation header has a link to the person's profile
            for selector in [
                ".msg-thread__link-to-profile",
                "a.app-aware-link[href*='/in/']",
                ".msg-s-event-listitem__link[href*='/in/']",
                ".presence-entity__image[href*='/in/']",
            ]:
                el = await self.page.query_selector(selector)
                if el:
                    href = await el.get_attribute("href")
                    if href and "/in/" in href:
                        # Clean up URL to just the profile path
                        match = re.search(r"(https?://[^/]*)?(/in/[^/?]+)", href)
                        if match:
                            return f"https://www.linkedin.com{match.group(2)}"
        except Exception:
            pass
        return None

    async def get_profile_data(self, profile_url: str) -> dict:
        if not profile_url:
            return {}
        try:
            print(f"  👤 Visiting profile: {profile_url}")
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            data = {}

            # Headline
            for sel in ["div.text-body-medium.break-words", ".pv-text-details__left-panel .text-body-medium"]:
                el = await self.page.query_selector(sel)
                if el:
                    data["headline"] = (await el.inner_text()).strip()
                    break

            # About section
            for sel in ["#about ~ div .pv-shared-text-with-see-more span[aria-hidden='true']",
                        "section[data-section='summary'] .pv-shared-text-with-see-more span"]:
                el = await self.page.query_selector(sel)
                if el:
                    data["about"] = (await el.inner_text()).strip()[:500]
                    break

            # Current role (first experience item)
            for sel in ["#experience ~ div li:first-child .mr1.t-bold span[aria-hidden='true']",
                        ".pvs-list__item--line-separated:first-child .mr1.hoverable-link-text span[aria-hidden='true']"]:
                el = await self.page.query_selector(sel)
                if el:
                    data["current_role"] = (await el.inner_text()).strip()
                    break

            # Recent posts / activity
            posts = []
            await self.page.goto(f"{profile_url}/recent-activity/all/", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            post_els = await self.page.query_selector_all(".feed-shared-update-v2__description span[aria-hidden='true']")
            for el in post_els[:3]:
                text = (await el.inner_text()).strip()
                if text and len(text) > 30:
                    posts.append(text[:300])
            if posts:
                data["recent_posts"] = posts

            return data
        except Exception as e:
            print(f"⚠️  Could not scrape profile: {e}")
            return {}

    async def get_conversation_messages(self, thread_id: str) -> list[dict]:
        try:
            await self.page.goto(
                f"https://www.linkedin.com/messaging/thread/{thread_id}/",
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(3)
            await self.page.wait_for_selector(".msg-s-message-list", timeout=15_000)
            await asyncio.sleep(1)

            messages = []
            events = await self.page.query_selector_all(".msg-s-event-listitem")

            for event in events:
                try:
                    body = await event.query_selector(".msg-s-event-listitem__body")
                    if not body:
                        continue
                    text = (await body.inner_text()).strip()
                    if not text:
                        continue

                    cls = await event.get_attribute("class") or ""
                    is_theirs = "other" in cls.lower()

                    messages.append({"role": "user" if is_theirs else "assistant", "content": text})
                except Exception:
                    continue

            return messages
        except Exception as e:
            print(f"⚠️  Error reading thread {thread_id}: {e}")
            return []

    async def send_message(self, thread_id: str, message: str) -> bool:
        try:
            await self.page.goto(
                f"https://www.linkedin.com/messaging/thread/{thread_id}/",
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(3)

            input_el = await self.page.wait_for_selector(
                ".msg-form__contenteditable", timeout=10_000
            )
            await input_el.click()
            await asyncio.sleep(0.5)

            await self.page.keyboard.press("Control+a")
            await asyncio.sleep(0.2)

            await input_el.type(message, delay=28)
            await asyncio.sleep(1)

            send_btn = await self.page.query_selector("button.msg-form__send-button")
            if send_btn:
                await send_btn.click()
            else:
                await input_el.press("Enter")

            await asyncio.sleep(2)
            return True
        except Exception as e:
            print(f"⚠️  Error sending to thread {thread_id}: {e}")
            return False
