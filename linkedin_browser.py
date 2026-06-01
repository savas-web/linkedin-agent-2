import asyncio
import re
import subprocess
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext


class LinkedInBrowser:
    def __init__(self, client_dir: Path, headless: bool = True):
        self.user_data_dir = str(client_dir / "linkedin_profile")
        self.headless = headless
        self.playwright = None
        self.context: BrowserContext = None
        self.page = None

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
        # If context is already open and healthy, reuse it — no close/reopen
        if self.context and self.page:
            try:
                _ = self.context.pages  # will raise if context is closed
                return
            except Exception:
                self.context = None
                self.page = None
        # Close any existing context before opening a new one
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
            self.page = None
            await asyncio.sleep(2)
        # Ensure no stale lock from a previous context
        Path(self.user_data_dir, "SingletonLock").unlink(missing_ok=True)
        # headless=False tells Playwright not to inject its own headless flags;
        # --headless=new passed directly to Chromium achieves true headless
        # without conflicting with the persistent profile format.
        args = [
            "--disable-gpu",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            "--disable-infobars",
            "--disable-notifications",
        ]
        if self.headless:
            args.append("--headless=new")
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            args=args,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self.page = await self.context.new_page()
        self.page.on("crash", lambda _: None)  # suppress unhandled crash exceptions

    async def stop_context(self):
        """Close the browser context only. Keeps the Playwright subprocess alive
        to avoid the CancelledError that playwright.stop() causes in Python 3.14.
        We do NOT pkill here — that kills Playwright's stdio pipes which crashes
        asyncio's kqueue selector. Let Playwright handle Chromium cleanup."""
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
            self.page = None
        # Give Chromium time to exit cleanly, then remove lock files
        await asyncio.sleep(2)
        Path(self.user_data_dir, "SingletonLock").unlink(missing_ok=True)
        Path(self.user_data_dir, "SingletonSocket").unlink(missing_ok=True)

    async def stop(self):
        """Full teardown — only call at process exit."""
        await self.stop_context()
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

    async def is_alive(self) -> bool:
        try:
            await self.page.evaluate("1")
            return True
        except Exception:
            # Page/renderer crashed — try recovering with a fresh page
            # before declaring the whole browser dead.
            try:
                self.page = await self.context.new_page()
                self.page.on("crash", lambda _: None)
                await self.page.evaluate("1")
                return True
            except Exception:
                return False

    async def restart(self):
        try:
            await self.stop_context()  # closes context + waits 2s + cleans locks
        except Exception:
            pass
        await asyncio.sleep(1)
        await self.start()
        await self.ensure_logged_in()
        print("  Browser restarted successfully.")

    async def is_logged_in(self) -> bool:
        try:
            url = self.page.url
            if any(x in url for x in ["login", "authwall", "checkpoint", "signup"]):
                return False
            if "linkedin.com" in url:
                return True
            # Use feed, not messaging — loading messaging marks conversations as read
            await self.page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15_000)
            await asyncio.sleep(2)
            url = self.page.url
            return not any(x in url for x in ["login", "authwall", "checkpoint", "signup"])
        except Exception:
            return False

    async def ensure_logged_in(self):
        await self.page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        if "login" in self.page.url or "authwall" in self.page.url or "checkpoint" in self.page.url:
            print("\n⚠️  Please log in to LinkedIn in the browser window.")
            print("The agent will continue once you're logged in...\n")
            await self.page.wait_for_url("**/messaging/**", timeout=180_000)
            await asyncio.sleep(3)
            print("✅ Logged in to LinkedIn!")

    async def _get_unread_names_from_page(self, url: str, unread_only: bool = False) -> list[str]:
        """Navigate to url and return names of (optionally unread-only) conversations."""
        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        try:
            await self.page.wait_for_selector("li.msg-conversation-listitem", timeout=20_000)
        except Exception:
            return []
        await asyncio.sleep(1)
        items = await self.page.query_selector_all("li.msg-conversation-listitem")
        names = []
        for item in items:
            try:
                if unread_only:
                    # Check for unread badge or bold indicator
                    badge = await item.query_selector(".notification-badge, .msg-conversation-card__unread-count, [class*='unread']")
                    if not badge:
                        # Check aria-label for "unread"
                        label = await item.get_attribute("aria-label") or ""
                        if "unread" not in label.lower():
                            continue
                name_el = await item.query_selector(".msg-conversation-card__participant-names span")
                name = (await name_el.inner_text()).strip() if name_el else None
                if name:
                    names.append(name)
            except Exception:
                continue
        return names

    async def get_unread_conversations(self) -> list[dict]:
        inbox_url = "https://www.linkedin.com/messaging/"
        try:
            await self.page.goto(inbox_url, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            try:
                await self.page.wait_for_selector("li.msg-conversation-listitem", timeout=20_000)
            except Exception:
                return []

            await asyncio.sleep(1)

            raw_items = await self.page.query_selector_all("li.msg-conversation-listitem")
            # Limit to first 15 conversations
            raw_items = raw_items[:15]
            print(f"  Scanning {len(raw_items)} conversations in inbox")

            candidate_names = []
            for item in raw_items:
                try:
                    name_el = await item.query_selector(".msg-conversation-card__participant-names span")
                    name = (await name_el.inner_text()).strip() if name_el else None
                    if name:
                        candidate_names.append(name)
                except Exception:
                    continue

            return await self._resolve_conversations(candidate_names, inbox_url)
        except Exception as e:
            print(f"⚠️  Error fetching conversations: {e}")
            return []

    async def _resolve_conversations(self, candidate_names: list[str], inbox_url: str) -> list[dict]:
        """Second pass — navigate to each conversation by name and extract thread_id."""
        results = []
        for name in candidate_names:
            try:
                await self.page.goto(inbox_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                all_items = await self.page.query_selector_all("li.msg-conversation-listitem")
                target = None
                for item in all_items:
                    try:
                        name_el = await item.query_selector(".msg-conversation-card__participant-names span")
                        item_name = (await name_el.inner_text()).strip() if name_el else ""
                        if item_name == name:
                            link_el = await item.query_selector(".msg-conversation-listitem__link")
                            if link_el:
                                target = link_el
                                break
                    except Exception:
                        continue

                if not target:
                    continue

                await target.click()
                await asyncio.sleep(2)

                url = self.page.url
                match = re.search(r"/messaging/thread/([^/?]+)", url)
                if not match:
                    continue

                thread_id = match.group(1)
                profile_url = await self._get_profile_url_from_conversation()

                results.append({
                    "thread_id": thread_id,
                    "name": name,
                    "profile_url": profile_url
                })

            except Exception:
                continue

        return results

    async def get_recent_posts(self, profile_url: str) -> list:
        if not profile_url:
            return []
        try:
            await self.page.goto(f"{profile_url}/recent-activity/all/", wait_until="domcontentloaded")
            await asyncio.sleep(2)
            post_els = await self.page.query_selector_all(".feed-shared-update-v2__description span[aria-hidden='true']")
            posts = []
            for el in post_els[:3]:
                text = (await el.inner_text()).strip()
                if text and len(text) > 30:
                    posts.append(text[:300])
            return posts
        except Exception:
            return []

    async def get_profile_url_from_conversation(self) -> str:
        return await self._get_profile_url_from_conversation()

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

    async def find_conversation_by_name(self, name: str) -> dict:
        """Search LinkedIn messaging for a person by name and return their messages + profile URL."""
        try:
            first_name = name.split()[0]
            await self.page.goto("https://www.linkedin.com/messaging/", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Type in the search box
            search_box = await self.page.query_selector(
                "input[placeholder*='Search'], .msg-conversations-search__search-input, input[type='text']"
            )
            if not search_box:
                print(f"⚠️  Could not find messaging search box")
                return {}

            await search_box.click()
            await asyncio.sleep(0.5)
            await search_box.type(first_name, delay=50)
            await asyncio.sleep(3)

            # Results may use different selectors than main inbox
            for sel in ["li.msg-conversation-listitem", ".msg-conversations-search__result-item", "li[class*='conversation']"]:
                items = await self.page.query_selector_all(sel)
                if items:
                    break

            # Dismiss any overlays
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            for item in items:
                name_el = await item.query_selector(
                    ".msg-conversation-card__participant-names span, .msg-entity-lockup__entity-title span"
                )
                item_name = (await name_el.inner_text()).strip() if name_el else ""

                if name.lower() in item_name.lower() or item_name.lower() in name.lower():
                    link_div = await item.query_selector(".msg-conversation-listitem__link, a")
                    target = link_div if link_div else item
                    # Use JS click to bypass overlay interception
                    await self.page.evaluate("el => el.click()", target)
                    await asyncio.sleep(2)

                    url = self.page.url
                    match = re.search(r"/messaging/thread/([^/?]+)", url)
                    if not match:
                        continue
                    thread_id = match.group(1)

                    profile_url = await self._get_profile_url_from_conversation()
                    messages = await self.get_conversation_messages(thread_id)

                    return {
                        "name": item_name,
                        "thread_id": thread_id,
                        "profile_url": profile_url or "",
                        "messages": messages
                    }
        except Exception as e:
            print(f"⚠️  Could not find conversation for {name}: {e}")
        return {}

    async def mark_as_unread(self, thread_id: str):
        try:
            await self.page.goto(
                f"https://www.linkedin.com/messaging/thread/{thread_id}/",
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(2)
            # Open the conversation options menu
            for sel in [
                "button.msg-thread-actions__control",
                "button[aria-label='More actions']",
                ".msg-thread__dropdown-trigger",
            ]:
                btn = await self.page.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    break
            # Click "Mark as unread"
            for sel in [
                "li[aria-label*='unread']",
                "div[aria-label*='unread']",
                "span:text('Mark as unread')",
            ]:
                opt = await self.page.query_selector(sel)
                if opt:
                    await opt.click()
                    await asyncio.sleep(1)
                    print(f"  ↩️  Marked thread {thread_id} as unread")
                    return
        except Exception as e:
            print(f"⚠️  Could not mark thread {thread_id} as unread: {e}")

    async def get_conversation_messages(self, thread_id: str) -> list[dict]:
        try:
            await self.page.goto(
                f"https://www.linkedin.com/messaging/thread/{thread_id}/",
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(3)
            await self.page.wait_for_selector(".msg-s-message-list", timeout=15_000)
            await asyncio.sleep(1)

            # Scroll to top of conversation to load full history
            msg_list = await self.page.query_selector(".msg-s-message-list")
            if msg_list:
                for _ in range(10):
                    await self.page.evaluate("document.querySelector('.msg-s-message-list').scrollTop = 0")
                    await asyncio.sleep(0.8)

            messages = []
            events = await self.page.query_selector_all(".msg-s-event-listitem")

            for event in events:
                try:
                    cls = await event.get_attribute("class") or ""
                    is_theirs = "other" in cls.lower()

                    body = await event.query_selector(".msg-s-event-listitem__body")
                    text = (await body.inner_text()).strip() if body else ""

                    if not text:
                        # Check if it's a media message (image, video, file, audio)
                        media = await event.query_selector(
                            "img.msg-image__image, video, .msg-audio-player, "
                            ".msg-file-attachment, .msg-s-event-listitem__gif"
                        )
                        if media:
                            messages.append({
                                "role": "user" if is_theirs else "assistant",
                                "content": "[media attachment — image, video, audio or file]",
                                "is_media": True
                            })
                        continue

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
