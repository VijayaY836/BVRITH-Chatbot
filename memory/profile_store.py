"""
Ex Memory-3: persistent user profiles across sessions.

Storage choice: a single plain JSON file (data/user_profiles.json), keyed by user_id,
guarded by a module-level threading.Lock. Picked over SQLite because this is a
single-process Streamlit app with a handful of profiles — a JSON file stays human
inspectable (useful for the Memory-5 privacy audit) and needs no schema migration.
Not safe across multiple OS processes; fine for this assignment's scope.
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "data" / "user_profiles.json"
STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()

PROFILE_TEMPLATE = {
    "user_id": None,
    "name": None,
    "branch_interest": None,
    "language": None,
    "detail_level": None,
    "prior_topics": [],
    "last_session_summary": None,
    "fee_amounts_discussed": [],
    "scholarship_details": [],
    "created_at": None,
    "last_accessed": None,
}

_LIST_UNIQUE_FIELDS = ("prior_topics", "scholarship_details")
_LIST_APPEND_FIELDS = ("fee_amounts_discussed",)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_all() -> dict:
    if not STORE_PATH.exists():
        return {}
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict) -> None:
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_profile(user_id: str) -> dict | None:
    with _lock:
        return _load_all().get(user_id)


def save_profile(user_id: str, profile: dict) -> None:
    with _lock:
        all_profiles = _load_all()
        all_profiles[user_id] = profile
        _save_all(all_profiles)


def update_profile(user_id: str, new_facts: dict) -> dict:
    """Merges new_facts into the stored profile (creating it if absent), updates
    last_accessed, and persists. List fields are merged (unique for topics/scholarships,
    appended for fee records) rather than overwritten."""
    with _lock:
        all_profiles = _load_all()
        existing = all_profiles.get(user_id)
        if existing is None:
            existing = {**PROFILE_TEMPLATE, "user_id": user_id, "created_at": _now()}

        merged = dict(existing)
        for key, value in new_facts.items():
            if key in _LIST_UNIQUE_FIELDS and isinstance(value, list):
                merged[key] = list(dict.fromkeys(merged.get(key, []) + value))
            elif key in _LIST_APPEND_FIELDS and isinstance(value, list):
                merged[key] = merged.get(key, []) + value
            else:
                merged[key] = value

        merged["last_accessed"] = _now()
        all_profiles[user_id] = merged
        _save_all(all_profiles)
        return merged
