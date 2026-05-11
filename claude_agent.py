import anthropic
import examples as ex

client = anthropic.Anthropic()


def _first_name(full_name: str) -> str:
    prefixes = {"dr.", "mr.", "mrs.", "ms.", "prof."}
    parts = full_name.strip().split()
    for part in parts:
        if part.lower().rstrip(".") + "." not in prefixes and part.lower() not in prefixes:
            return part
    return parts[0] if parts else full_name


def generate_followup(last_message: str, name: str, cfg: dict = None) -> str:
    cfg = cfg or {}
    claude_model = cfg.get("claude_model", "claude-sonnet-4-6")
    first = _first_name(name)
    system = (
        f"You are writing a single casual follow-up LinkedIn message on behalf of {cfg.get('agent_name', 'the user')}.\n\n"
        f"The last message sent to {first} was:\n\"{last_message}\"\n\n"
        f"They have not replied. Write one short, warm, human follow-up nudge. "
        f"Examples of the right tone: 'Hey {first}, just wanted to bump this up in case it got buried!' or "
        f"'Hey {first}, was just thinking about my last message — still keen to connect if the timing works?' "
        f"Keep it to 1 sentence. Use only their first name ({first}). Never repeat or paraphrase the last message. No sales language."
    )
    response = client.messages.create(
        model=claude_model,
        max_tokens=100,
        system=system,
        messages=[{"role": "user", "content": f"Write the follow-up message for {name}."}]
    )
    return response.content[0].text.strip()


def generate_reply(conversation: list[dict], profile: dict = None, cfg: dict = None):
    if not conversation:
        return None

    cfg = cfg or {}
    system_prompt = cfg.get("system_prompt", "")
    claude_model = cfg.get("claude_model", "claude-sonnet-4-6")
    agent_name = cfg.get("agent_name", "Max")

    messages = list(conversation)
    leading = []
    while messages and messages[0]["role"] != "user":
        leading.append(messages.pop(0))
    if not messages:
        return None

    trailing = []
    while messages and messages[-1]["role"] == "assistant":
        trailing.insert(0, messages.pop())
    if not messages and not trailing:
        return None
    if not messages:
        messages = [{"role": "user", "content": "[No reply from prospect yet]"}]

    system = system_prompt
    if leading:
        system += f"\n\nFIRST MESSAGE(S) {agent_name.upper()} ALREADY SENT BEFORE THE PROSPECT REPLIED:\n"
        for m in leading:
            system += f"{agent_name}: {m['content']}\n"
        system += "The conversation below starts with the prospect's reply to the above.\n"
    if trailing:
        system += f"\n\n{agent_name.upper()} ALREADY SENT THIS AS THE LAST MESSAGE AND THE PROSPECT HAS NOT REPLIED:\n"
        for m in trailing:
            system += f"{agent_name}: {m['content']}\n"
        system += (
            "Write a very short, casual follow-up nudge. "
            "The tone should feel like a real person just checking in — something like 'Hey [name], just wanted to bump this up in case it got lost!' or 'Hey [name], was just thinking about my last message — still keen to connect if the timing works?' "
            "Keep it to 1 or 2 sentences max. Warm, zero pressure, completely natural. "
            "Never repeat or paraphrase the last message. Never sound salesy or formal.\n"
        )
    system += ex.build_examples_prompt(agent_name)

    if profile:
        lines = [f"\n\n--- PROSPECT PROFILE DATA (this is specifically for {profile.get('name', 'this person')}) ---"]
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
        lines.append("Only reference details from THIS profile. Do not mix in details from any other person.")
        system += "\n".join(lines)

    clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    response = client.messages.create(
        model=claude_model,
        max_tokens=300,
        system=system,
        messages=clean_messages
    )
    return response.content[0].text.strip()
