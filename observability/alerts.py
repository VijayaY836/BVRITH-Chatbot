"""Ex Obs-3: threshold alerts and input validation."""
import datetime

from observability.logger import log_event

THRESHOLDS = {
    "latency_s": 10,
    "cost_per_query_usd": 0.10,
    "error_rate_pct": 5,  # rolling last 20 queries
}


def check_alerts(call_log: list[dict]) -> list[str]:
    """Returns human-readable warning strings for any breached threshold, else []."""
    if not call_log:
        return []

    warnings = []

    last = call_log[-1]
    last_latency_s = last["latency_ms"] / 1000
    if last_latency_s > THRESHOLDS["latency_s"]:
        warnings.append(
            f"⚠️ Latency alert: last call took {last_latency_s:.1f}s "
            f"(threshold {THRESHOLDS['latency_s']}s)."
        )

    if last.get("call_type") == "rag_generation" and last.get("estimated_cost_usd", 0) > THRESHOLDS["cost_per_query_usd"]:
        warnings.append(
            f"⚠️ Cost alert: last query cost ${last['estimated_cost_usd']:.4f} "
            f"(threshold ${THRESHOLDS['cost_per_query_usd']:.2f})."
        )

    window = call_log[-20:]
    if len(window) >= 5:  # don't fire on tiny samples
        error_rate_pct = 100 * sum(1 for c in window if c.get("status") == "failure") / len(window)
        if error_rate_pct > THRESHOLDS["error_rate_pct"]:
            warnings.append(
                f"⚠️ Error rate alert: {error_rate_pct:.1f}% of the last {len(window)} calls failed "
                f"(threshold {THRESHOLDS['error_rate_pct']}%)."
            )

    return warnings


def validate_input_length(user_input: str, max_chars: int = 2000) -> tuple[bool, str | None]:
    """Returns (is_valid, rejection_message). Logs rejected attempts."""
    if len(user_input) > max_chars:
        message = (
            f"Your message is too long ({len(user_input)} characters). "
            f"Please shorten it to under {max_chars} characters and try again."
        )
        log_event({
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "call_type": "rejected_input",
            "model": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 0.0,
            "estimated_cost_usd": 0.0,
            "status": "failure",
            "error": f"input length {len(user_input)} exceeds max_chars {max_chars}",
        })
        return False, message
    return True, None
