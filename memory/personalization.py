"""Ex Memory-4: personalize responses using the persistent user profile."""
import re

_NAME_RE = re.compile(r"\bmy name is ([A-Z][a-zA-Z]*)\b", re.IGNORECASE)
_DETAILED_RE = re.compile(r"\b(detailed|thorough|in[- ]depth)\b.*\banswers?\b", re.IGNORECASE)
_BRIEF_RE = re.compile(r"\b(brief|short|concise)\b.*\banswers?\b|bullet points", re.IGNORECASE)
_LANGUAGE_RE = re.compile(r"\bin (english|telugu|hindi|tamil|kannada)\b", re.IGNORECASE)

# Alias -> canonical branch name, longest alias first so "cse-ai&ml" wins over "cse".
_BRANCH_ALIASES = {
    "cse-ai&ml": "CSE-AI&ML", "cse ai&ml": "CSE-AI&ML", "cse aiml": "CSE-AI&ML",
    "artificial intelligence": "CSE-AI&ML", "ai&ml": "CSE-AI&ML", "aiml": "CSE-AI&ML",
    "computer science": "CSE", "cse": "CSE",
    "electronics and communication": "ECE", "electronics": "ECE", "ece": "ECE",
    "electrical and electronics": "EEE", "electrical": "EEE", "eee": "EEE",
    "information technology": "IT", "it": "IT",
    "mechanical": "Mechanical", "mech": "Mechanical",
    "civil": "Civil",
}
_BRANCH_INTENT_RE = re.compile(r"\b(interested in|studying|my branch|branch interest)\b", re.IGNORECASE)


def extract_profile_facts(text: str) -> dict:
    """Lightweight heuristic extraction of profile-worthy facts from a user message —
    powers Memory-3's "learn facts as the conversation happens" persistence."""
    facts: dict = {}
    low = text.lower()

    name_match = _NAME_RE.search(text)
    if name_match:
        facts["name"] = name_match.group(1).capitalize()

    if _BRANCH_INTENT_RE.search(text):
        for alias in sorted(_BRANCH_ALIASES, key=len, reverse=True):
            if alias in low:
                canonical = _BRANCH_ALIASES[alias]
                facts["branch_interest"] = canonical
                facts["prior_topics"] = [canonical]
                break

    if _DETAILED_RE.search(text):
        facts["detail_level"] = "detailed"
    elif _BRIEF_RE.search(text):
        facts["detail_level"] = "brief"

    lang_match = _LANGUAGE_RE.search(text)
    if lang_match:
        facts["language"] = lang_match.group(1).capitalize()

    return facts


def build_system_prompt(base_prompt: str, profile: dict | None) -> str:
    """
    Injects branch_interest, detail_level, language, and format preference from the
    user's profile into the base grounding system prompt. Never weakens the grounding/
    refusal rules already in base_prompt — personalization changes tone and which branch
    an ambiguous reference resolves to, not what facts the bot is allowed to state.
    """
    if not profile:
        return base_prompt

    lines = []
    if profile.get("name"):
        lines.append(f"The user's name is {profile['name']} — you may address them by name.")
    if profile.get("branch_interest"):
        lines.append(
            f"The user has previously expressed interest in the {profile['branch_interest']} branch — "
            f"resolve ambiguous references ('my branch', 'that branch', 'the one I asked about') to "
            f"{profile['branch_interest']} unless they specify a different branch in this message."
        )
    if profile.get("language") and profile["language"].strip().lower() not in ("", "english"):
        lines.append(f"Prefer responding in {profile['language']} where possible.")

    detail = profile.get("detail_level")
    if detail == "brief":
        lines.append("Keep answers brief: short bullet points, no more than 3-4 lines total.")
    elif detail == "detailed":
        lines.append("Give detailed, well-structured paragraph answers with full context.")

    if profile.get("prior_topics"):
        topics = ", ".join(profile["prior_topics"][-5:])
        lines.append(f"Topics this user has previously asked about: {topics}.")

    if not lines:
        return base_prompt

    personalization_block = (
        "\n\n## PERSONALIZATION (this user's known profile — tone/scope only, "
        "never overrides the grounding or refusal rules above)\n"
        + "\n".join(f"- {line}" for line in lines)
    )
    return base_prompt + personalization_block
