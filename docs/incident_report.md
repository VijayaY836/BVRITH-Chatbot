# Incident Report — Simulated Week

## Anomalies

### Wednesday
1. **Root cause:** 3 users pasted an entire document/page as a single query (input_tokens ~15000 vs normal ~1200), driving cost to $4.82 (16.3x baseline) with no input length cap live at the time.
2. **Metric that would have caught it:** input_tokens per call (or estimated_cost_usd per query)
3. **Alert threshold:** Enforce the existing 0.1 USD-per-query alert (observability/alerts.py) AND add a hard input-length cap before the call — already implemented as validate_input_length(max_chars=2000) in Ex Obs-3.
4. **Production fix:** Enforce the 2000-char input validator (Obs-3) and/or a hard input-token cap before sending to the LLM.

### Friday
1. **Root cause:** 12 errors, type RateLimitError, clustered in 16:00-17:00 — a traffic spike (or shared API-key rate limit) exhausted the account's rate limit; latency outside that window was normal (2.4s) but the day's average was pulled up to 8.5s (3.9x baseline).
2. **Metric that would have caught it:** error rate by hour, and rolling error_rate_pct over the last 20 calls
3. **Alert threshold:** The existing rolling error-rate alert (threshold 5%, observability/alerts.py) would have caught this in near-real-time instead of a weekly review.
4. **Production fix:** Add exponential backoff + retry on 429s, request queueing, and/or an upgraded rate-limit tier.

## Monitoring dashboard sketch
- A **cost-per-query time series** panel would show a sharp spike on Wednesday (3 outlier points at ~$1.47/query vs a ~$0.003/query baseline).
- An **error-rate-by-hour heatmap** would show a dark cell for Friday 16:00-17:00 (12 errors clustered in one hour) against an otherwise all-zero week.

## Dean-facing summary
This week we had two short-lived incidents, both now caught by automated alerts we've since turned on. On Wednesday, a few users pasted very large blocks of text into the chatbot, which briefly spiked our AI usage cost — we've added a message-length limit so this can't happen again. On Friday, a burst of traffic during one hour temporarily exceeded our AI provider's rate limit, causing some requests to fail or run slowly for about an hour — we're adding automatic retries and monitoring so this recovers on its own and pages us immediately if it recurs. No student data was lost or exposed in either incident.
