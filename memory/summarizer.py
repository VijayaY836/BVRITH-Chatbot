"""Ex Memory-2: rolling summarization so long conversations don't blow up the context window."""
from typing import Callable

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def count_tokens(text: str) -> int:
    """Real tokenizer count via tiktoken; falls back to a chars/4 estimate if unavailable."""
    if _ENC is not None:
        return len(_ENC.encode(text))
    return max(1, len(text) // 4)


def should_summarize(history, every_n_turns: int = 10) -> bool:
    """True exactly when the conversation has just crossed a multiple of every_n_turns messages."""
    n = history.turn_count()
    return n > 0 and n % every_n_turns == 0


def summarize_older_turns(older_messages: list[dict], llm_call_fn: Callable[[list], str]) -> str:
    """
    Produces a paragraph summary preserving:
    - user's name (if stated)
    - branches/topics asked about
    - specific facts discussed (fee amounts, dates)
    - stated preferences ("prefer CSE", "explain briefly")
    - unresolved questions/follow-up threads

    llm_call_fn receives a list of {"role", "content"} messages and returns the response text
    (empty string on failure) — callers are expected to route this through logged_llm_call.
    """
    if not older_messages:
        return ""

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in older_messages)
    prompt = (
        "Summarize the following conversation in ONE paragraph. You MUST preserve:\n"
        "- the user's name, if stated\n"
        "- branches/topics they asked about\n"
        "- specific facts discussed (fee amounts, dates, figures)\n"
        "- stated preferences (e.g. 'prefer CSE', 'explain briefly')\n"
        "- any unresolved questions or follow-up threads\n\n"
        f"Conversation:\n{transcript}\n\nSummary:"
    )
    messages = [
        {
            "role": "system",
            "content": "You compress conversation history into a single faithful paragraph. "
                       "Never invent facts not present in the transcript.",
        },
        {"role": "user", "content": prompt},
    ]
    result = llm_call_fn(messages)
    return (result or "").strip()


def build_context_messages(history, summary_cache: dict, llm_call_fn: Callable[[list], str],
                            every_n_turns: int = 10) -> list[dict]:
    """
    Returns the message list to actually send to the LLM: if the conversation is short,
    the raw history; otherwise a cached rolling summary (system message) + the last
    `every_n_turns` raw turns. `summary_cache` is a mutable dict the caller persists
    across turns (e.g. st.session_state.summary_cache), shape: {"text": str, "up_to": int}.
    """
    n = history.turn_count()
    if n <= every_n_turns:
        return history.as_messages()

    if should_summarize(history, every_n_turns) or not summary_cache.get("text"):
        older = history.head_before_tail(every_n_turns)
        summary_cache["text"] = summarize_older_turns(older, llm_call_fn)
        summary_cache["up_to"] = n - every_n_turns

    tail_messages = [{"role": m["role"], "content": m["content"]} for m in history.tail(every_n_turns)]
    if not summary_cache.get("text"):
        return history.as_messages()
    return [{"role": "system", "content": f"Earlier conversation summary: {summary_cache['text']}"}] + tail_messages
