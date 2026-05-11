import json
from datetime import datetime, timezone
from pathlib import Path

_analytics_file = Path("analytics.json")
DEAD_DAYS = 14


def init(client_dir: Path):
    global _analytics_file
    _analytics_file = client_dir / "analytics.json"


def load() -> dict:
    if not _analytics_file.exists():
        return {}
    with open(_analytics_file) as f:
        return json.load(f)


def save(data: dict):
    with open(_analytics_file, "w") as f:
        json.dump(data, f, indent=2)


def _detect_stage(messages: list, calendly_link: str) -> str:
    our = [m for m in messages if m["role"] == "assistant"]
    theirs = [m for m in messages if m["role"] == "user"]

    if calendly_link:
        for m in our:
            if calendly_link in m.get("content", ""):
                return "calendly_sent"

    if not theirs:
        return "new"
    if len(our) + len(theirs) >= 6:
        return "warm"
    return "replied"


def update_conversation(thread_id: str, name: str, messages: list, calendly_link: str = ""):
    data = load()
    now = datetime.now(timezone.utc).isoformat()
    existing = data.get(thread_id, {})

    our = [m for m in messages if m["role"] == "assistant"]
    theirs = [m for m in messages if m["role"] == "user"]
    stage = _detect_stage(messages, calendly_link)

    data[thread_id] = {
        "name": name,
        "first_seen": existing.get("first_seen", now),
        "last_activity": now,
        "messages_sent": len(our),
        "messages_received": len(theirs),
        "stage": stage,
        "agent_sent_at": existing.get("agent_sent_at", None),
        "follow_up_count": existing.get("follow_up_count", 0),
        "last_follow_up_at": existing.get("last_follow_up_at", None),
    }
    save(data)


def record_agent_sent(thread_id: str):
    data = load()
    if thread_id in data:
        data[thread_id]["agent_sent_at"] = datetime.now(timezone.utc).isoformat()
        save(data)


def record_followup(thread_id: str):
    data = load()
    if thread_id in data:
        data[thread_id]["follow_up_count"] = data[thread_id].get("follow_up_count", 0) + 1
        data[thread_id]["last_follow_up_at"] = datetime.now(timezone.utc).isoformat()
        save(data)


def get_followup_candidates(max_follow_ups: int, follow_up_days: int) -> list:
    data = load()
    now = datetime.now(timezone.utc)
    threshold = follow_up_days * 86400
    candidates = []
    for thread_id, conv in data.items():
        if not conv.get("agent_sent_at"):
            continue
        if conv.get("follow_up_count", 0) >= max_follow_ups:
            continue
        reference = conv.get("last_follow_up_at") or conv.get("agent_sent_at")
        try:
            age = (now - datetime.fromisoformat(reference)).total_seconds()
        except Exception:
            continue
        if age >= threshold:
            candidates.append({"thread_id": thread_id, "name": conv.get("name", "")})
    return candidates


def get_summary() -> dict:
    data = load()
    now = datetime.now(timezone.utc)
    counts = {"new": 0, "replied": 0, "warm": 0, "calendly_sent": 0, "dead": 0}

    for conv in data.values():
        stage = conv.get("stage", "new")
        try:
            last = datetime.fromisoformat(conv.get("last_activity", ""))
            if (now - last).days >= DEAD_DAYS and conv.get("messages_received", 0) == 0:
                stage = "dead"
        except Exception:
            pass
        counts[stage] = counts.get(stage, 0) + 1

    return {"total": len(data), "stages": counts}
