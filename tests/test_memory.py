"""
Acceptance tests for the Memory layer (spec.MD section 3).

These call the *real* chatbot pipeline (app.answer_question), which makes real
OpenRouter API calls — they are integration tests, not unit tests with a mocked LLM,
matching the spec's "run this exact script and record every response" acceptance bar.
"""
import pytest

from app import answer_question
from memory import profile_store
from memory.history import ConversationHistory
from memory.personalization import build_system_prompt, extract_profile_facts
from memory.privacy import auto_expire_profiles, clear_user_data, is_clear_data_command


@pytest.fixture
def isolated_profile_store(tmp_path, monkeypatch):
    """Redirects the profile JSON store to a throwaway file so tests never touch
    the real data/user_profiles.json."""
    fake_path = tmp_path / "user_profiles.json"
    monkeypatch.setattr(profile_store, "STORE_PATH", fake_path)
    return fake_path


# ── Ex Memory-1: multi-turn conversation ────────────────────────────────────────

def test_multiturn_script():
    """5-turn scripted conversation; each turn's answer must contain the required fact."""
    history = ConversationHistory()
    transcript = []

    def ask(question):
        chat_history = [(m["role"], m["content"]) for m in history.as_messages()]
        answer, _ = answer_question(question, chat_history=chat_history)
        history.add("user", question)
        history.add("assistant", answer)
        transcript.append((question, answer))
        return answer

    a1 = ask("What B.Tech branches does BVRIT offer?")
    assert "CSE" in a1

    a2 = ask("Tell me more about the first one.")
    assert "CSE" in a2

    a3 = ask("What's the fee for that branch?")
    assert "CSE" in a3 and any(c.isdigit() for c in a3)

    a4 = ask("My name is Priya.")
    assert len(a4) > 0  # acknowledgment of some form

    a5 = ask("What's my name and which branch was I asking about?")
    assert "Priya" in a5
    assert "CSE" in a5

    assert len(transcript) == 5


# ── Ex Memory-3: persistent profile across a fresh process ─────────────────────

def test_profile_persists_across_fresh_load(isolated_profile_store):
    """Simulates a new process by re-reading from disk rather than reusing an in-memory ref."""
    user_id = "test_priya"
    profile_store.update_profile(user_id, {
        "name": "Priya", "branch_interest": "CSE", "language": "English", "detail_level": "detailed",
    })

    # "Fresh process": load straight from the file the first call wrote to disk.
    reloaded = profile_store.load_profile(user_id)
    assert reloaded is not None
    assert reloaded["name"] == "Priya"
    assert reloaded["branch_interest"] == "CSE"


def test_session2_recalls_branch_and_name_without_repetition(isolated_profile_store):
    user_id = "test_priya2"
    profile_store.update_profile(user_id, {"name": "Priya", "branch_interest": "CSE"})
    profile = profile_store.load_profile(user_id)

    answer, _ = answer_question("What's the fee for the branch I'm interested in?", profile=profile)
    assert "CSE" in answer

    answer2, _ = answer_question("What's my name?", profile=profile)
    assert "Priya" in answer2


# ── Ex Memory-4: personalization changes content and style ─────────────────────

def test_personalization_varies_by_profile():
    priya = {"name": "Priya", "branch_interest": "CSE", "detail_level": "detailed", "language": "English"}
    rahul = {"name": "Rahul", "branch_interest": "Mechanical", "detail_level": "brief", "language": "English"}

    base = "BASE PROMPT TEXT"
    prompt_priya = build_system_prompt(base, priya)
    prompt_rahul = build_system_prompt(base, rahul)

    assert prompt_priya != prompt_rahul
    assert "CSE" in prompt_priya and "Mechanical" not in prompt_priya
    assert "Mechanical" in prompt_rahul and "CSE" not in prompt_rahul
    assert "detailed" in prompt_priya
    assert "brief" in prompt_rahul


def test_extract_profile_facts():
    facts = extract_profile_facts("My name is Priya and I'm interested in B.Tech CSE.")
    assert facts["name"] == "Priya"
    assert facts["branch_interest"] == "CSE"

    facts2 = extract_profile_facts("I prefer detailed answers in English.")
    assert facts2["detail_level"] == "detailed"
    assert facts2["language"] == "English"


# ── Ex Memory-5: right to be forgotten ──────────────────────────────────────────

def test_clear_my_data_deletes_profile(isolated_profile_store):
    user_id = "test_forget_me"
    profile_store.update_profile(user_id, {"name": "Someone"})
    assert profile_store.load_profile(user_id) is not None

    assert is_clear_data_command("Clear My Data")  # case-insensitive
    deleted = clear_user_data(user_id)
    assert deleted is True
    assert profile_store.load_profile(user_id) is None

    # Clearing again reports nothing existed
    assert clear_user_data(user_id) is False


def test_auto_expire_profiles(isolated_profile_store):
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    all_profiles = {
        "stale_user": {**profile_store.PROFILE_TEMPLATE, "user_id": "stale_user",
                       "last_accessed": (now - timedelta(days=31)).isoformat()},
        "fresh_user": {**profile_store.PROFILE_TEMPLATE, "user_id": "fresh_user",
                       "last_accessed": (now - timedelta(days=29)).isoformat()},
    }
    profile_store._save_all(all_profiles)

    expired = auto_expire_profiles(max_age_days=30)

    assert "stale_user" in expired
    assert "fresh_user" not in expired
    assert profile_store.load_profile("stale_user") is None
    assert profile_store.load_profile("fresh_user") is not None
