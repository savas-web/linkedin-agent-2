import json
from pathlib import Path


def load(client_name: str) -> dict:
    client_dir = Path("clients") / client_name
    with open(client_dir / "config.json") as f:
        cfg = json.load(f)
    prompt_file = client_dir / "system_prompt.txt"
    system_prompt = prompt_file.read_text().strip()

    # Load custom prompt additions if they exist
    additions_file = client_dir / "custom_additions.json"
    if additions_file.exists():
        with open(additions_file) as f:
            additions_data = json.load(f)
            if additions_data.get("additions"):
                system_prompt += "\n\n## Custom Instructions\n\n"
                for addition in additions_data["additions"]:
                    system_prompt += f"- {addition}\n"

    cfg["system_prompt"] = system_prompt
    cfg["client_dir"] = client_dir
    cfg["client_name"] = client_name
    return cfg
