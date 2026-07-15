"""Ex Obs-5: diagnose production problems from a week of (simulated) logs."""
import json
from pathlib import Path
from statistics import mean

from observability.alerts import THRESHOLDS

ROOT = Path(__file__).resolve().parent.parent
LOGS_PATH = ROOT / "data" / "simulated_week_logs.json"
REPORT_PATH = ROOT / "docs" / "incident_report.md"


def load_week() -> dict:
    return json.loads(LOGS_PATH.read_text(encoding="utf-8"))


def detect_anomalies(week: dict) -> list[dict]:
    """Baseline off Monday/Tuesday (the two days with no reported anomaly), then flag any
    day whose cost or latency deviates sharply, or whose error count is non-trivial."""
    baseline_days = [week["monday"], week["tuesday"]]
    baseline_cost = mean(d["total_cost_usd"] for d in baseline_days)
    baseline_latency = mean(d["avg_latency_s"] for d in baseline_days)

    anomalies = []
    for day, data in week.items():
        if day in ("monday", "tuesday"):
            continue
        cost_ratio = data["total_cost_usd"] / baseline_cost if baseline_cost else 0
        latency_ratio = data["avg_latency_s"] / baseline_latency if baseline_latency else 0
        if cost_ratio > 3:
            anomalies.append({"day": day, "type": "cost_spike", "ratio": round(cost_ratio, 1), "data": data})
        if latency_ratio > 2 or data["errors"] > 5:
            anomalies.append({"day": day, "type": "latency_or_error_spike", "ratio": round(latency_ratio, 1), "data": data})
    return anomalies


def diagnose(anomalies: list[dict]) -> list[dict]:
    diagnoses = []
    for a in anomalies:
        d = a["data"]
        if a["type"] == "cost_spike":
            detail = d.get("detail", {})
            diagnoses.append({
                "day": a["day"],
                "root_cause": (
                    f"{detail.get('anomalous_queries', '?')} users pasted an entire document/page as a "
                    f"single query (input_tokens ~{detail.get('anomalous_input_tokens', '?')} vs normal "
                    f"~{detail.get('normal_input_tokens', '?')}), driving cost to ${d['total_cost_usd']:.2f} "
                    f"({a['ratio']}x baseline) with no input length cap live at the time."
                ),
                "catching_metric": "input_tokens per call (or estimated_cost_usd per query)",
                "alert_threshold": (
                    f"Enforce the existing {THRESHOLDS['cost_per_query_usd']} USD-per-query alert "
                    "(observability/alerts.py) AND add a hard input-length cap before the call — "
                    "already implemented as validate_input_length(max_chars=2000) in Ex Obs-3."
                ),
                "fix": "Enforce the 2000-char input validator (Obs-3) and/or a hard input-token cap before sending to the LLM.",
            })
        else:  # latency_or_error_spike
            detail = d.get("detail", {})
            diagnoses.append({
                "day": a["day"],
                "root_cause": (
                    f"{d['errors']} errors, type {detail.get('error_type', 'unknown')}, clustered in "
                    f"{detail.get('error_window', 'a narrow window')} — a traffic spike (or shared API-key rate "
                    f"limit) exhausted the account's rate limit; latency outside that window was normal "
                    f"({detail.get('avg_latency_outside_window_s', '?')}s) but the day's average was pulled up to "
                    f"{d['avg_latency_s']}s ({a['ratio']}x baseline)."
                ),
                "catching_metric": "error rate by hour, and rolling error_rate_pct over the last 20 calls",
                "alert_threshold": (
                    f"The existing rolling error-rate alert (threshold {THRESHOLDS['error_rate_pct']}%, "
                    "observability/alerts.py) would have caught this in near-real-time instead of a weekly review."
                ),
                "fix": "Add exponential backoff + retry on 429s, request queueing, and/or an upgraded rate-limit tier.",
            })
    return diagnoses


def write_report(diagnoses: list[dict]) -> None:
    lines = ["# Incident Report — Simulated Week", "", "## Anomalies", ""]
    for d in diagnoses:
        lines += [
            f"### {d['day'].capitalize()}",
            f"1. **Root cause:** {d['root_cause']}",
            f"2. **Metric that would have caught it:** {d['catching_metric']}",
            f"3. **Alert threshold:** {d['alert_threshold']}",
            f"4. **Production fix:** {d['fix']}",
            "",
        ]

    lines += [
        "## Monitoring dashboard sketch",
        "- A **cost-per-query time series** panel would show a sharp spike on Wednesday "
        "(3 outlier points at ~$1.47/query vs a ~$0.003/query baseline).",
        "- An **error-rate-by-hour heatmap** would show a dark cell for Friday 16:00-17:00 "
        "(12 errors clustered in one hour) against an otherwise all-zero week.",
        "",
        "## Dean-facing summary",
        "This week we had two short-lived incidents, both now caught by automated alerts we've since turned on. "
        "On Wednesday, a few users pasted very large blocks of text into the chatbot, which briefly spiked our "
        "AI usage cost — we've added a message-length limit so this can't happen again. On Friday, a burst of "
        "traffic during one hour temporarily exceeded our AI provider's rate limit, causing some requests to fail "
        "or run slowly for about an hour — we're adding automatic retries and monitoring so this recovers "
        "on its own and pages us immediately if it recurs. No student data was lost or exposed in either incident.",
        "",
    ]

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run():
    week = load_week()
    anomalies = detect_anomalies(week)
    diagnoses = diagnose(anomalies)
    write_report(diagnoses)
    print(f"Detected {len(anomalies)} anomalies across {len(week)} days.")
    print(f"Report written to {REPORT_PATH}")
    return diagnoses


if __name__ == "__main__":
    run()
