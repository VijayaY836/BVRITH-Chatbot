"""Ex Obs-2: session stats aggregation for the sidebar dashboard."""

EMPTY_STATS = {
    "total_queries": 0,
    "avg_latency_s": 0.0,
    "p95_latency_s": 0.0,
    "total_cost_usd": 0.0,
    "total_tokens": 0,
    "error_count": 0,
}


def compute_session_stats(call_log: list[dict]) -> dict:
    """
    call_log is the list of records produced by observability.logger.logged_llm_call.
    total_queries counts user-facing RAG generations; the other five stats aggregate
    over every logged call (tool/summarization/judge calls all have real cost/latency).
    """
    if not call_log:
        return dict(EMPTY_STATS)

    latencies = [c["latency_ms"] / 1000 for c in call_log]
    total_cost = sum(c.get("estimated_cost_usd", 0.0) for c in call_log)
    total_tokens = sum(c.get("input_tokens", 0) + c.get("output_tokens", 0) for c in call_log)
    error_count = sum(1 for c in call_log if c.get("status") == "failure")
    query_calls = [c for c in call_log if c.get("call_type") == "rag_generation"]

    sorted_lat = sorted(latencies)
    p95_index = min(len(sorted_lat) - 1, int(round(0.95 * (len(sorted_lat) - 1))))
    p95 = sorted_lat[p95_index] if sorted_lat else 0.0

    return {
        "total_queries": len(query_calls) or len(call_log),
        "avg_latency_s": round(sum(latencies) / len(latencies), 3),
        "p95_latency_s": round(p95, 3),
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "error_count": error_count,
    }
