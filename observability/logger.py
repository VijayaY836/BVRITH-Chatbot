"""Ex Obs-1: wrap every LLM call with logging."""
import datetime
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "llm_calls.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Hardcoded per-1M-token USD pricing (OpenAI's published rates, passed through by
# OpenRouter as of 2025). Refresh against https://openrouter.ai/api/v1/models if rates change.
PRICING_PER_1M_TOKENS = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "openai/text-embedding-3-small": {"input": 0.02, "output": 0.0},
}
DEFAULT_PRICING = {"input": 0.50, "output": 1.50}

# "test_generation" is an addition beyond the spec's base 5 call_types, for evaluate.py's
# LLM #1 (test-case generator) — kept distinct from "judge" (LLM #3) for cost attribution.
VALID_CALL_TYPES = {"rag_generation", "tool_call", "summarization", "judge", "ab_test", "test_generation"}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING_PER_1M_TOKENS.get(model, DEFAULT_PRICING)
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def _append_jsonl(record: dict) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def log_event(record: dict) -> None:
    """Append a non-LLM-call event (e.g. a rejected input) to the same JSONL log."""
    _append_jsonl(record)
    _append_to_session_log(record)


def _append_to_session_log(record: dict) -> None:
    """Best-effort: only succeeds inside a running Streamlit session."""
    try:
        import streamlit as st
        st.session_state.setdefault("call_log", []).append(record)
    except Exception:
        pass


def logged_llm_call(*, model: str, messages: list, call_type: str, llm_client, **kwargs) -> dict:
    """
    Wraps an OpenAI-compatible chat.completions.create call.

    On every call (success or failure) appends one record to data/llm_calls.jsonl and,
    if running inside Streamlit, to st.session_state.call_log.

    Error-handling strategy (picked once, used everywhere): never raises — always
    returns {"content": ..., "log_entry": {...}}. On failure "content" is None and
    log_entry["status"] == "failure" with the error message.
    """
    if call_type not in VALID_CALL_TYPES:
        raise ValueError(f"Unknown call_type: {call_type!r} (expected one of {VALID_CALL_TYPES})")

    start = time.perf_counter()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        response = llm_client.chat.completions.create(model=model, messages=messages, **kwargs)
        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0

        record = {
            "timestamp": timestamp,
            "call_type": call_type,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": round(latency_ms, 2),
            "estimated_cost_usd": round(_estimate_cost(model, input_tokens, output_tokens), 6),
            "status": "success",
            "error": None,
        }
        _append_jsonl(record)
        _append_to_session_log(record)
        return {"content": response.choices[0].message.content, "log_entry": record}

    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        record = {
            "timestamp": timestamp,
            "call_type": call_type,
            "model": model,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": round(latency_ms, 2),
            "estimated_cost_usd": 0.0,
            "status": "failure",
            "error": str(e),
        }
        _append_jsonl(record)
        _append_to_session_log(record)
        return {"content": None, "log_entry": record}
