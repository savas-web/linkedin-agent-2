import anthropic
from config import SYSTEM_PROMPT, CLAUDE_MODEL

client = anthropic.Anthropic()

def generate_reply(conversation: list[dict], profile: dict = None):
    if not conversation:
        return None

    if conversation[0]["role"] != "user":
        conversation = conversation[1:]
    if not conversation:
        return None

    system = SYSTEM_PROMPT
    if profile:
        lines = ["\n\n--- PROSPECT PROFILE DATA ---"]
        if profile.get("headline"):
            lines.append(f"Headline: {profile['headline']}")
        if profile.get("current_role"):
            lines.append(f"Current role: {profile['current_role']}")
        if profile.get("about"):
            lines.append(f"About: {profile['about']}")
        if profile.get("recent_posts"):
            lines.append("Recent posts:")
            for p in profile["recent_posts"]:
                lines.append(f"  - {p}")
        lines.append("Use this to make your reply feel genuinely personal. Reference something specific if it fits naturally.")
        system += "\n".join(lines)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=system,
        messages=conversation
    )
    return response.content[0].text.strip()
