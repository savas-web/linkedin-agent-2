import json
from pathlib import Path

STATE_FILE = Path("state.json")

DEFAULT_STATE = {
    "total_sent": 0,
    "pending_approvals": {},   # approval_id -> {thread_id, name, their_message, proposed_reply, tg_message_id}
    "approved_queue": [],      # [{thread_id, message}]
    "awaiting_edit": None      # approval_id waiting for user to type edited reply
}

def load() -> dict:
    if not STATE_FILE.exists():
        save(DEFAULT_STATE.copy())
    with open(STATE_FILE) as f:
        return json.load(f)

def save(data: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)
