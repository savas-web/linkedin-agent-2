import json
from pathlib import Path

_state_file = Path("state.json")

DEFAULT_STATE = {
    "total_sent": 0,
    "weekly_sent": 0,
    "last_report_week": "",
    "pending_approvals": {},
    "approved_queue": [],
    "awaiting_edit": None,
    "sent_hashes": []
}


def init(client_dir: Path):
    global _state_file
    _state_file = client_dir / "state.json"


def load() -> dict:
    if not _state_file.exists():
        save(DEFAULT_STATE.copy())
    with open(_state_file) as f:
        return json.load(f)


def save(data: dict):
    with open(_state_file, "w") as f:
        json.dump(data, f, indent=2)
