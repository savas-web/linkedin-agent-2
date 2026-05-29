import json
from pathlib import Path
from datetime import datetime

_examples_file = Path("examples.json")
MAX_EXAMPLES = 30


def init(client_dir: Path):
    global _examples_file
    _examples_file = client_dir / "examples.json"


def load() -> list[dict]:
    if not _examples_file.exists():
        return []
    with open(_examples_file) as f:
        return json.load(f)


def save_edit(their_message: str, ai_draft: str, max_sent: str):
    examples = load()
    examples.append({
        "their_message": their_message,
        "ai_draft": ai_draft,
        "max_sent": max_sent,
        "timestamp": datetime.now().isoformat()
    })
    examples = examples[-MAX_EXAMPLES:]
    with open(_examples_file, "w") as f:
        json.dump(examples, f, indent=2)


def build_examples_prompt(agent_name: str = "Max") -> str:
    examples = load()
    if not examples:
        return ""

    lines = [
        f"\n\n════════════════════════════════════════",
        f"CRITICAL — LEARN FROM {agent_name.upper()}'S EDITS",
        f"════════════════════════════════════════",
        f"{agent_name} has manually corrected your drafts multiple times.",
        f"These corrections are your most important instructions. They override your defaults.",
        f"Before writing anything, read every example below. Identify the PATTERN of what you kept getting wrong.",
        f"Do NOT repeat the same mistakes.\n",
        f"For each example:",
        f"  THEIR MESSAGE = what the prospect said",
        f"  YOUR DRAFT    = what you wrote (the mistake)",
        f"  {agent_name.upper()} CHANGED IT TO = the correct version\n",
        f"Study what specifically changed. Is it length? Opening line? Tone? Pushback removed? Call to action removed?",
        f"Apply those exact corrections to your next reply.\n",
    ]

    for i, ex in enumerate(examples[-15:], 1):
        ai = ex['ai_draft'][:250]
        sent = ex['max_sent'][:250]
        their = ex['their_message'][:150]
        lines.append(f"── Edit {i} ──")
        lines.append(f"  THEIR MESSAGE:  {their}")
        lines.append(f"  YOUR DRAFT:     {ai}")
        lines.append(f"  {agent_name.upper()} CHANGED TO: {sent}")

        # Highlight obvious differences
        ai_words = len(ai.split())
        sent_words = len(sent.split())
        if sent_words < ai_words * 0.6:
            lines.append(f"  ⚠️  {agent_name} made it MUCH SHORTER ({ai_words} → {sent_words} words)")
        elif sent_words > ai_words * 1.4:
            lines.append(f"  ⚠️  {agent_name} made it LONGER ({ai_words} → {sent_words} words)")
        if ai[:30].lower() != sent[:30].lower():
            lines.append(f"  ⚠️  {agent_name} changed the OPENING LINE")
        lines.append("")

    lines.append("════════════════════════════════════════\n")
    return "\n".join(lines)
