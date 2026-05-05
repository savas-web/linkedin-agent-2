import anthropic
import examples as ex

client = anthropic.Anthropic()


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

    system = system_prompt
    if leading:
        system += f"\n\nFIRST MESSAGE(S) {agent_name.upper()} ALREADY SENT BEFORE THE PROSPECT REPLIED:\n"
        for m in leading:
            system += f"{agent_name}: {m['content']}\n"
        system += "The conversation below starts with the prospect's reply to the above.\n"
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
