"""Ex Memory-1: in-session conversation history."""
from datetime import datetime, timezone
from typing import Optional


class ConversationHistory:
    def __init__(self):
        self.messages: list[dict] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def as_messages(self) -> list[dict]:
        """Role/content only, ready to feed into an LLM call."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def clear(self) -> None:
        self.messages = []

    def turn_count(self) -> int:
        return len(self.messages)

    def tail(self, n: int) -> list[dict]:
        return self.messages[-n:] if n > 0 else []

    def head_before_tail(self, n: int) -> list[dict]:
        """All messages except the last n — the ones eligible for summarization."""
        return self.messages[:-n] if n > 0 else list(self.messages)
