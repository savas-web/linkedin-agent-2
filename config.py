import json
from pathlib import Path


def load(client_name: str) -> dict:
    client_dir = Path("clients") / client_name
    with open(client_dir / "config.json") as f:
        cfg = json.load(f)
    prompt_file = client_dir / "system_prompt.txt"
    cfg["system_prompt"] = prompt_file.read_text().strip()
    cfg["client_dir"] = client_dir
    cfg["client_name"] = client_name
    return cfg
