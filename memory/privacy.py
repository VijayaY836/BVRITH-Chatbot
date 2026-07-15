"""
Ex Memory-5: right to be forgotten.

Field classification (see FIELD_CLASSIFICATION below — also referenced by the
governance report):

| Field                         | Classification                                                     |
|--------------------------------|----------------------------------------------------------------------|
| name                            | SENSITIVE (PII)                                                       |
| branch_interest                 | NICE-TO-HAVE                                                          |
| language                        | NICE-TO-HAVE                                                          |
| detail_level                    | NICE-TO-HAVE                                                          |
| prior_topics                    | NICE-TO-HAVE                                                          |
| last_session_summary             | NICE-TO-HAVE (may contain PII incidentally — review)                  |
| full_conversation_transcripts    | SENSITIVE — do not store by default                                  |
| fee_amounts_discussed            | ESSENTIAL (for the fee-recall feature)                                |
| scholarship_details              | SENSITIVE if tied to caste/category (SC/ST/OBC scholarship names)     |
"""
from datetime import datetime, timezone

from memory.profile_store import _load_all, _save_all

FIELD_CLASSIFICATION = {
    "name": "SENSITIVE (PII)",
    "branch_interest": "NICE-TO-HAVE",
    "language": "NICE-TO-HAVE",
    "detail_level": "NICE-TO-HAVE",
    "prior_topics": "NICE-TO-HAVE",
    "last_session_summary": "NICE-TO-HAVE (may contain PII incidentally — review)",
    "full_conversation_transcripts": "SENSITIVE — do not store by default",
    "fee_amounts_discussed": "ESSENTIAL (for the fee-recall feature)",
    "scholarship_details": "SENSITIVE if tied to caste/category (SC/ST/OBC scholarship names)",
}

PRIVACY_NOTICE = (
    "This assistant remembers your name, branch interest, and preferences across visits "
    "to personalize your experience — for example, recalling your branch so you don't "
    "repeat it. It does not store full conversation transcripts. Type **'clear my data'** "
    "at any time to permanently delete your profile. Inactive profiles are automatically "
    "deleted after 30 days."
)


def is_clear_data_command(user_input: str) -> bool:
    return user_input.strip().lower() == "clear my data"


def clear_user_data(user_id: str) -> bool:
    """Deletes the persistent profile. Returns True if a profile existed and was deleted."""
    all_profiles = _load_all()
    existed = user_id in all_profiles
    if existed:
        del all_profiles[user_id]
        _save_all(all_profiles)
    return existed


def auto_expire_profiles(max_age_days: int = 30) -> list[str]:
    """Deletes and returns user_ids not accessed in max_age_days. Call on app startup."""
    all_profiles = _load_all()
    now = datetime.now(timezone.utc)
    expired = []
    for user_id, profile in list(all_profiles.items()):
        last_accessed = profile.get("last_accessed")
        if not last_accessed:
            continue
        try:
            last_dt = datetime.fromisoformat(last_accessed)
        except ValueError:
            continue
        if (now - last_dt).days >= max_age_days:
            expired.append(user_id)
            del all_profiles[user_id]
    if expired:
        _save_all(all_profiles)
    return expired
