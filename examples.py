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
        f"\n\n--- LEARNING FROM {agent_name.upper()}'S EDITS ---",
        f"Below are real examples where the AI draft was edited by {agent_name} before sending.",
        f"Study the difference in tone, phrasing and style. Write more like the '{agent_name} sent' version.\n"
    ]
    for i, ex in enumerate(examples[-15:], 1):
        lines.append(f"Example {i}:")
        lines.append(f"  Their message: {ex['their_message'][:200]}")
        lines.append(f"  AI draft:      {ex['ai_draft'][:200]}")
        lines.append(f"  {agent_name} sent:      {ex['max_sent'][:200]}\n")

    return "\n".join(lines)
