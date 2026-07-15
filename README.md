# BVRIT FAQ Chatbot

A RAG-powered chatbot that answers questions about **BVRIT Hyderabad Women's College** (bvrit.ac.in) using a curated knowledge base — with cited answers, graceful refusals on out-of-scope questions, and an automated 8-dimension evaluation suite.

Built for the *GenAI & Agentic AI Engineering* lab assignment (see [spec.MD](spec.MD) for the full technical spec).

## How it works

1. **Knowledge base** — a curated Word doc (`BVRITH_Chatbot_Knowledge_Base.docx`) covering About, Departments, Admissions, Fee Structure, Placements, Facilities, Faculty, and Contact, plus supplementary pages scraped from the college website (`scraped_knowledge.md`).
2. **Ingestion** — the doc and scraped pages are loaded, split into chunks (`RecursiveCharacterTextSplitter`, 400/120), and embedded into a **ChromaDB** vector store persisted locally in `chroma_db/` (survives restarts).
3. **Retrieval** — a query is embedded and matched against the vector store, re-ranked with keyword overlap, and assembled into context.
4. **Generation** — an OpenRouter-hosted LLM (`gpt-4o-mini` by default) answers strictly from the retrieved context, citing `[Section, Page]` for every claim, and refuses gracefully instead of guessing when the answer isn't in the knowledge base.
5. **Special-case tools** — fee questions are routed to a deterministic calculator (`fee_calculator.py`) and date questions to a regex-based date checker (`date_checker.py`), bypassing the LLM for exact figures.
6. **Evaluation** — `evaluate.py` runs a 20+ case, 8-dimension test suite (functional, quality, safety, security, robustness, performance, context, RAGAS) against the live chatbot and produces a structured pass/fail report; `eval_ui.py` provides a Streamlit dashboard to view it.
7. **Memory** — conversations persist within a session (`memory/history.py`), roll into a summary once they get long (`memory/summarizer.py`), and optionally persist across sessions under a user-supplied ID (`memory/profile_store.py`), personalizing tone/branch resolution (`memory/personalization.py`) with a "clear my data" forget-me command (`memory/privacy.py`).
8. **Observability** — every LLM call (generation, summarization, judge, A/B) is logged with cost/latency/token counts (`observability/logger.py`), aggregated into a live sidebar dashboard (`observability/metrics.py`), checked against alert thresholds with input-length validation (`observability/alerts.py`), and can be A/B tested at the prompt level (`observability/ab_test.py`).
9. **Governance** — a vulnerability scan, red-team probes, quality-metric scoring, and a fairness audit (`governance/`) run against the live chatbot; findings feed a governed system prompt (`app.GOVERNED_SYSTEM_PROMPT`) that is now the actual production prompt, plus a full governance report (`governance/report/governance_report.md`).

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit chat app — ingestion, retrieval, generation, UI, wires in memory + observability |
| `fee_calculator.py` | Deterministic fee/scholarship lookup, bypasses the LLM for exact numbers |
| `date_checker.py` | Extracts and classifies dates (past/upcoming) from context |
| `scraper.py` | Crawls bvrit.ac.in to build `scraped_knowledge.md` / `scraped_chunks.json` |
| `extract_images.py` | Pulls images out of the knowledge base `.docx` |
| `evaluate.py` | Runs the 8-dimension automated evaluation suite, writes `evaluation_report.json` |
| `eval_ui.py` | Streamlit dashboard for browsing the evaluation report |
| `knowledge.md` / `scraped_knowledge.md` | Human-readable knowledge sources |
| `chroma_db/` | Persisted vector store (generated, gitignored) |
| `memory/` | Conversation history, summarization, user profiles, personalization, privacy |
| `observability/` | LLM call logging, session metrics, alerts, prompt A/B testing, incident analysis |
| `tests/` | Pytest suite covering the memory and observability acceptance criteria |
| `data/` | Runtime logs (`llm_calls.jsonl`, `user_profiles.json`, `ab_test_results.jsonl` — all gitignored, may contain PII) plus the `simulated_week_logs.json` fixture |
| `docs/` | Generated reports: `ab_test_summary.md`, `incident_report.md` |
| `governance/` | Vulnerability scan, red-team, quality metrics, fairness audit, governed system prompt, and the final governance report (`governance/report/`) |

## What changed since Day 4 (spec.MD's Day 5 layer)

Day 4 shipped a stateless RAG chatbot. Day 5 adds two layers on top **without changing Day-4 behavior** (verified via `evaluate.py` regression — same pass rate as baseline):

- **Memory** — the bot now remembers the conversation (with rolling summarization past 10 turns so long chats don't blow up the context window), can recall a user's name/branch/preferences across separate sessions if they supply a User ID in the sidebar, personalizes tone and branch-resolution accordingly, and honors a typed `"clear my data"` command to permanently delete a stored profile (with 30-day auto-expiry for inactive ones).
- **Observability** — every LLM call anywhere in the codebase (generation, summarization, evaluation judge, A/B test) is now routed through `logged_llm_call`, which records latency/cost/token counts to `data/llm_calls.jsonl` and powers a live "Session Stats" sidebar panel, threshold-based alerts (latency/cost/error-rate), a 2000-character input length cap, and a script to A/B test the grounding prompt's strictness (`observability/ab_test.py`).

- **Governance** — rather than installing the actual `giskard`/`promptfoo`/`deepeval` libraries (heavy dependencies, Node.js for promptfoo, multi-minute scans), the Governance layer is built as lightweight in-house equivalents (`governance/scan.py`, `redteam.py`, `quality_metrics.py`, `fairness_audit.py`) that reuse the same live-chatbot + LLM-judge infrastructure already wired up for `evaluate.py`. This found one real issue — the bot gave a dismissive, unhelpful answer to Telugu-language requests versus English ones — which is now fixed in `app.GOVERNED_SYSTEM_PROMPT`, the **production** system prompt (see `governance/report/governance_report.md` for the full writeup, before/after re-scan numbers, and EU AI Act / India DPDP Act risk classification).

## Setup

1. Create a `.env` file from `.env.example` and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_key_here
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the chatbot:
   ```
   streamlit run app.py
   ```
4. Run the evaluation suite:
   ```
   python evaluate.py
   ```
5. (Optional) View evaluation results in a dashboard:
   ```
   streamlit run eval_ui.py
   ```
6. Run the memory + observability test suite:
   ```
   pytest tests/ -v
   ```
   Note: `tests/test_memory.py` calls the real chatbot pipeline (real OpenRouter API calls) to verify multi-turn recall, persistence, and personalization end-to-end — expect it to take under a minute and use a small amount of API credit. `tests/test_observability.py` is pure logic/unit tests (no API calls).
7. (Optional) Run the grounding-prompt A/B test (~20 real API calls, writes `docs/ab_test_summary.md`):
   ```
   python -m observability.ab_test
   ```
8. (Optional) Regenerate the simulated-incident diagnosis (`docs/incident_report.md`, no API calls):
   ```
   python -m observability.incident_sim
   ```

## Notes

- The primary knowledge base is `BVRITH_Chatbot_Knowledge_Base.docx`; scraped site pages supplement it.
- The vector store is persisted locally in `chroma_db/` — delete this folder to force a full re-index (e.g. after changing the embedding model or knowledge base).
- The evaluation report is written to `evaluation_report.json`.
- `.env` holds secrets and is excluded via `.gitignore` — never commit real API keys.
