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

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit chat app — ingestion, retrieval, generation, UI |
| `fee_calculator.py` | Deterministic fee/scholarship lookup, bypasses the LLM for exact numbers |
| `date_checker.py` | Extracts and classifies dates (past/upcoming) from context |
| `scraper.py` | Crawls bvrit.ac.in to build `scraped_knowledge.md` / `scraped_chunks.json` |
| `extract_images.py` | Pulls images out of the knowledge base `.docx` |
| `evaluate.py` | Runs the 8-dimension automated evaluation suite, writes `evaluation_report.json` |
| `eval_ui.py` | Streamlit dashboard for browsing the evaluation report |
| `knowledge.md` / `scraped_knowledge.md` | Human-readable knowledge sources |
| `chroma_db/` | Persisted vector store (generated, gitignored) |

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

## Notes

- The primary knowledge base is `BVRITH_Chatbot_Knowledge_Base.docx`; scraped site pages supplement it.
- The vector store is persisted locally in `chroma_db/` — delete this folder to force a full re-index (e.g. after changing the embedding model or knowledge base).
- The evaluation report is written to `evaluation_report.json`.
- `.env` holds secrets and is excluded via `.gitignore` — never commit real API keys.
