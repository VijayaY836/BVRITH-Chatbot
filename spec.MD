# BVRIT College FAQ Chatbot — Technical Spec

**Assignment:** GenAI & Agentic AI Engineering · Day 4 Afternoon Lab
**Type:** RAG-powered chatbot with 8-dimension automated evaluation
**Time budget:** 60 minutes build + evaluation
**No scaffold** — full design + implementation from scratch

---

## 1. Goal

Build a RAG chatbot that answers questions about BVRIT (bvrit.ac.in) using only a
curated Word document as its knowledge base, cites section + page for every
answer, refuses gracefully on out-of-scope questions, and ships with an
automated 8-dimension test suite (including RAGAS) that produces a structured
evaluation report.

**Definition of done** (from the brief, verbatim scope — don't build past this):
- Document loads → chunks → embeds → persists in a vector store that survives a restart.
- Streamlit chat UI: user asks, gets an answer with a visible citation to a section.
- Out-of-scope questions get a graceful refusal, not a hallucination.
- ≥20 LLM-generated test cases across all 8 dimensions, each with an expected answer.
- All test cases run against the live chatbot; LLM-as-judge scores expected vs actual.
- A structured evaluation report: pass/fail per dimension, RAGAS scores, weakest dimension, one specific fix recommendation.
- Survives peer review: partner asks 3 uncovered questions; bot answers correctly or refuses appropriately.

Stretch goals (multi-turn memory, section filter, auto-fix loop, chunking A/B
test, visual dashboard) are optional and out of scope unless the core list
above is done and time remains.

---

## 2. Tech Stack

| Component | Choice |
|---|---|
| Orchestration | LangChain |
| Document loader | `Docx2txtLoader` |
| Text splitter | `RecursiveCharacterTextSplitter` |
| Embedding model | `text-embedding-3-small` (OpenAI, via OpenRouter, 1536-dim) — same model for index + query |
| Vector database | ChromaDB, local persistent storage |
| Generation LLM | GPT-4o Mini via OpenRouter (upgrade path: Claude Sonnet / GPT-4o) |
| Judge LLM | A **different** model from the generation LLM (avoid self-bias) |
| UI | Streamlit (`st.chat_input`, `st.chat_message`, sidebar) |
| Evaluation | RAGAS (faithfulness, answer relevancy, context precision, context recall) |

---

## 3. Knowledge Base (Phase 0)

Source: bvrit.ac.in — About, Departments, Admissions, Fee Structure,
Placements, Facilities, Contact. Copied into one Word doc with distinct
H1/H2 headings per section (the chunker depends on these).

Required sections, in order:

1. **About BVRIT** — history, vision, mission, accreditations (NAAC, NBA)
2. **Departments** — B.Tech branches, specialisations, faculty count
3. **Admissions** — eligibility, entrance exams (EAMCET, JEE), process, key dates
4. **Fee Structure** — tuition by branch, hostel fees, other charges, scholarships
5. **Placements** — top recruiters, avg/highest package, placement %
6. **Campus & Facilities** — library, labs, hostel, sports, WiFi, transport
7. **Faculty** — key faculty, qualifications, research areas
8. **Contact** — address, phone, email, website, social media

Rules: factual content only, no marketing copy; never invent a fact not on
the site. Missing-fact-in-doc → chatbot refuses. That refusal is a feature.

---

## 4. Ingestion & Indexing (Phase 1)

- Load the Word doc with `Docx2txtLoader`.
- Split with `RecursiveCharacterTextSplitter`, using the section headings as
  natural break points. Pick a chunk size + overlap and **write down the
  justification** (tradeoff: small chunks → precise retrieval but less
  context per chunk; large chunks → more context but noisier retrieval).
- Every chunk carries metadata: at minimum `source_filename` and
  `section_heading`. This is required for later metadata filtering and for
  citations.
- Persist the Chroma store to disk. Verify persistence explicitly: reload
  the store in a fresh process and confirm chunk count matches the original
  index run. Print total chunk count as a sanity check.

---

## 5. Retrieval (Phase 2)

- Build a retriever over the persisted store.
- `top_k` starts at 5, tune from there — too low misses context, too high
  dilutes the answer.
- Optional: metadata filter by `section_heading` (e.g. scope a fee question
  to the Fee Structure section only). This is the mechanism the sidebar
  section-filter dropdown (Phase 4 / stretch) hooks into.
- **Before wiring up generation**, test retrieval standalone: run 3 known
  queries, print retrieved chunks, confirm the right chunks come back. If
  retrieval is wrong, fix it before touching the prompt — no amount of
  prompt engineering fixes bad retrieval.

---

## 6. Grounded Generation (Phase 3)

The generation prompt is the single highest-leverage piece of this build.
It must enforce all five of the following, not just describe them:

1. **Role** — "You are the BVRIT college information assistant."
2. **Grounding rule** — answer ONLY from the retrieved context passed in
   this call; never fall back to training/world knowledge about BVRIT or
   colleges in general.
3. **Citation format** — every factual claim cites `[Section Name, Page N]`.
   Page number comes from the loader's page metadata (or heading-based
   pseudo-page if the loader doesn't expose real pages — state which you
   used).
4. **Refusal instruction** — if the answer isn't in the retrieved context,
   say so explicitly and provide a fallback (e.g. "point the user to the
   Contact section / official website"). Never guess.
5. **Conflict handling** — if two retrieved chunks disagree, present both
   and flag the discrepancy rather than silently picking one.

Sanity check before moving on: ask something you know is **not** in the
document. The bot must refuse, not produce a plausible-sounding invented
answer.

---

## 7. Chat UI (Phase 4)

Streamlit single-page app.

**Sidebar:**
- Loaded document name + total chunk count
- Retrieval params in use: chunk size, overlap, top_k
- (Optional) section-filter dropdown

**Main area:**
- Chat interface via `st.chat_input` / `st.chat_message`
- Every bot response shows its citation(s) inline or directly below the answer
- Conversation history persists within the session (Streamlit session state)

---

## 8. Eight-Dimension Evaluation Suite (Phase 5)

Three-LLM pattern:
- **LLM #1 (Test Generator)** — strong model (GPT-4o / Claude Sonnet), fed
  the grounding document, produces test cases + expected answers per dimension.
- **LLM #2 (System Under Test)** — your live chatbot (GPT-4o Mini).
- **LLM #3 (Judge)** — a **different** model from LLM #2, scores expected vs
  actual per dimension's specific criteria.
- **RAGAS** — Dimension 08 only, runs as code (not an LLM prompt call).

### 8.1 Test case generation — target: 20 cases minimum

| # | Dimension | Cases | What it checks |
|---|---|---|---|
| 01 | Functional | 3 | Follows spec: cited answers, format constraints, completeness (e.g. list-all-departments question — every dept from doc must appear) |
| 02 | Quality | 3 | Factual accuracy, exact figures (fees, placement %), coherent structure |
| 03 | Safety | 2 | No outcome guarantees ("will I get placed"), no bias, no medical/legal/financial advice |
| 04 | Security | 2 | Prompt injection resistance — "ignore previous instructions", system prompt leakage attempts |
| 05 | Robustness | 3 | Edge inputs: empty string, gibberish, very long input, emoji-only, mixed English+Telugu/Hindi — no crash, no hallucination from nothing |
| 06 | Performance | 2 | Latency on a simple query and a complex multi-section query against a defined SLA (e.g. <10s) |
| 07 | Context | 2 | Multi-turn: turn 2 correctly resolves a reference from turn 1 (e.g. "the first one") |
| 08 | RAGAS | 3 | Programmatic scoring: faithfulness, answer relevancy, context precision, context recall |

Each generated test case record needs: `question`, `expected_answer`,
`dimension`, `pass_fail_criteria`.

### 8.2 Running the suite

For every test case, capture: `dimension`, `question`, `expected_answer`,
`actual_response`, `retrieved_chunks` (needed for dims 01–02 and RAGAS),
`latency_seconds` (needed for dim 06).

### 8.3 Judging (per-dimension criteria)

| Dimension | Judge checks |
|---|---|
| Functional | Format followed? Citations present? Answer complete? |
| Quality | Facts match expected? Anything hallucinated or missing? |
| Safety | Refused/disclaimed where expected? Any harmful promise/claim? |
| Security | Stayed in role? Any system info leaked? Did injection succeed? |
| Robustness | Handled edge case gracefully? No crash? No hallucination from nothing? |
| Performance | Numerical SLA check, not LLM judgment |
| Context | Did the follow-up correctly reference the prior turn? |
| RAGAS | Report all four scores as computed by the library |

Judge output per test case: structured pass/fail + reason string.

### 8.4 Evaluation report (required deliverable)

Must contain, in this shape:

- **Summary** — total cases, passed, failed, warning, overall pass rate
- **Per-dimension breakdown** — pass/fail count for each of the 8 dimensions
- **Weakest dimension** — named explicitly, with the specific reason it's weak
- **Recommended fix** — one concrete, actionable fix tied to the weakest dimension
- **RAGAS scores** — faithfulness, answer relevancy, context precision, context recall (numeric)
- **RAGAS diagnosis** — one sentence naming the lowest RAGAS metric and a concrete lever to pull (e.g. reduce chunk_size, add metadata filters) if context precision is the weak point

A chatbot without this report is a demo, not a deliverable — treat report
generation as a required build step, not an afterthought.

---

## 9. Peer Review Readiness

A partner will ask 3 questions not in your test set. The bot must either
answer correctly (with citation) or refuse appropriately — no hallucination
under novel questions.

---

## 10. Explicitly Out of Scope (unless time remains)

- Multi-turn memory beyond what Dimension 07 requires to test context (full
  conversational memory is a stretch goal)
- Section-filter dropdown (stretch)
- Auto-fix retry loop on failed judge verdicts (stretch, max 2 retries if built)
- Chunk-size A/B comparison (stretch)
- Separate visual dashboard tab beyond what's needed to present the Step D report (stretch)

Build the core list in Section 1 first. Only reach for stretch goals once
every item in the "Done by 3:00" list is actually done.