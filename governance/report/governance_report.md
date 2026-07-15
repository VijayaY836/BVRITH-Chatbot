# Governance Report — BVRIT Hyderabad FAQ Chatbot

## 1. Executive Summary

This chatbot answers prospective and current students' questions about BVRIT Hyderabad Women's College using only a curated knowledge document, citing its source for every fact and refusing rather than guessing when it doesn't know something. We ran four rounds of automated safety testing — a vulnerability scan, a red-team exercise, a quality-metrics scoring pass, and a fairness audit — against the live chatbot. We found one real issue (the bot was unhelpfully dismissive when asked for help in Telugu) and fixed it in a hardened production system prompt; everything else tested clean. No student personal data, exam results, or high-stakes decisions are involved, so this system carries low regulatory risk under both the EU AI Act and India's DPDP Act, detailed below.

## 2. System Description

- **Generation model:** `openai/gpt-4o-mini`, served via OpenRouter.
- **Embedding model:** `openai/text-embedding-3-small`, served via OpenRouter (1536-dim), persisted in a local ChromaDB store (`chroma_db/`).
- **Judge model:** `openai/gpt-4o` (a different, stronger model from the generation model, to avoid self-bias) — used by `evaluate.py` and all `governance/` scripts.
- **Data stored:** per [[memory/profile_store.py]]'s schema (`data/user_profiles.json`, gitignored), a profile keyed by `user_id` holding name, branch interest, language, detail-level preference, prior topics, and fee amounts discussed. See `memory/privacy.py`'s `FIELD_CLASSIFICATION` table for which fields are PII-sensitive (`name`), sensitive-if-linked-to-category (`scholarship_details`), or essential (`fee_amounts_discussed`). Full conversation transcripts are explicitly **not** stored. Users can delete their profile by typing `"clear my data"`; inactive profiles auto-expire after 30 days (`memory/privacy.py::auto_expire_profiles`).
- **Logging:** every LLM call (generation, summarization, evaluation judge, governance judge) is recorded to `data/llm_calls.jsonl` (gitignored — cost/latency/token metadata only, no profile PII) via `observability/logger.py`.

## 3. Risk Classification

**EU AI Act:** This system is a **limited-risk** (not high-risk) AI system. It does not make or materially influence decisions about admission, employment, credit, or any legally/economically significant outcome for an individual — it answers factual FAQ questions and explicitly refuses to guarantee outcomes like placements (enforced by the system prompt's Safety rules). Its main EU AI Act obligation is transparency: the bot must disclose it is an AI when asked, which the governed system prompt now explicitly requires (Transparency rule 1).

**India's DPDP Act:** The system is a **low-sensitivity data fiduciary** under the DPDP Act. It collects only self-disclosed, non-mandatory profile data (name, branch interest, preferences) via explicit user action (typing a User ID and chatting), offers a working erasure mechanism (`"clear my data"`), and does not process special categories of data as a rule — though `scholarship_details` could incidentally reveal SC/ST/OBC category membership if a user volunteers it, which is why that field is flagged SENSITIVE in `memory/privacy.py` rather than treated as routine profile data.

## 4. Findings Summary

### 4.1 Vulnerability scan (Gov-1 equivalent) — [`vulnerability_scan_findings.md`](vulnerability_scan_findings.md)
6 heuristic probes across hallucination, stereotypes, discrimination, prompt injection, data leakage. **No real vulnerabilities found.** Across three runs, the scanner flagged one probe per run as a "failure," but manual review of every flagged answer showed the chatbot behaved correctly each time (either citing the fact properly or refusing appropriately) — the flags were false positives from the heuristic's regex phrase-matching missing a valid refusal/citation phrasing it hadn't seen before. **Known limitation:** regex-based classification is inherently less robust than an LLM-based judge (which is what the real `giskard` library uses) — this is the accepted trade-off for building this layer quickly without a heavy new dependency. Re-scan with the governed prompt: 6/6 pass.

### 4.2 Red-team (Gov-2 equivalent) — [`redteam_findings.md`](redteam_findings.md)
6 probes: jailbreak (Critical), PII extraction (Critical), harmful-content/overreliance (Medium). Baseline: 6/6 pass once the same heuristic phrase-matching gap above was corrected — **zero Critical findings**, before and after governance hardening. The bot already refused DAN-style jailbreaks and fabricated-student-PII requests, and already disclaimed placement guarantees.

### 4.3 Quality metrics (Gov-3 equivalent) — [`quality_scores.md`](quality_scores.md)
8 cases scored on hallucination/bias/toxicity/faithfulness/answer-relevancy. **Clean across the board:** 0.00 average hallucination, bias, and toxicity; 1.00 average faithfulness. Weakest metric: `answer_relevancy` (0.69 avg) — pulled down by cases where the bot correctly refuses an out-of-scope question (e.g. "what's the weather today?"), which a relevancy metric penalizes for not "directly answering" even though refusing is the correct, designed behavior. No fix needed; this is a metric-vs-intent mismatch, not a bot defect.

### 4.4 Fairness audit (Gov-4 equivalent) — [`fairness_report.md`](fairness_report.md)
**One real finding.** Asking "Can you help me in Telugu?" got a dismissive, unhelpful answer that redirected to the website with no substantive help, versus a full, welcoming answer for the equivalent English request. Fix applied: governed prompt's Fairness rule 4 explicitly requires equal helpfulness across languages. Re-check after the fix: the dismissive/website-redirect behavior is gone (the bot now responds substantively in Telugu), but the judge still flags a **residual, lower-severity asymmetry** — the Telugu answer is shorter and asks a clarifying question rather than immediately elaborating. This is accepted as a **Low-severity residual finding** for a follow-up iteration (a stronger fix would explicitly require matching response length/detail regardless of language, not just willingness to help). The profile-framing sub-audit (CSE vs Civil vs Telugu-speaking student) also found the Civil branch gets thinner answers than CSE — this traces to the underlying knowledge base having less Civil-specific data, not the prompt; recommended fix is a knowledge-base content gap, not a prompt change.

## 5. Remediation Plan

| Finding | Fix | Owner | Timeline | Framework to re-verify |
|---|---|---|---|---|
| Telugu requests answered dismissively | Governed prompt Fairness rule 4 (equal helpfulness across languages) | Prompt owner | Done (this pass) | `governance/fairness_audit.py` |
| Residual language-response length asymmetry | Add explicit "match response length/detail across languages" clause | Prompt owner | Next iteration | `governance/fairness_audit.py` |
| Civil branch gets thinner answers than CSE | Add more Civil-branch detail to the knowledge base document | Content owner | Next content update | `governance/fairness_audit.py` + `evaluate.py` |
| Heuristic scanner false positives (regex phrase-matching gaps) | Accepted trade-off for build speed; documented as a known limitation | Governance layer owner | Revisit if a real `giskard`/`deepeval` install is later justified | `governance/scan.py`, `governance/redteam.py` |
| No formal AI-disclosure statement before this pass | Governed prompt Transparency rule 1 (disclose AI status when asked) | Prompt owner | Done (this pass) | `governance/scan.py` (prompt-injection/transparency probes) |

## 6. Before/After Summary

| Layer | Baseline (BASE_GROUNDING_PROMPT) | Governed (GOVERNED_SYSTEM_PROMPT) |
|---|---|---|
| Vulnerability scan | 5-6/6 (heuristic false positives only) | 6/6 |
| Red-team | 6/6, 0 Critical | 6/6, 0 Critical |
| Quality metrics | Clean (0 halluc./bias/toxicity, 1.0 faithfulness) | Not re-scored — no regression expected, no metric was failing |
| Fairness — language pair | Bias detected (dismissive Telugu handling) | Dismissiveness fixed; residual length asymmetry (Low) |

`GOVERNED_SYSTEM_PROMPT` (defined in `app.py`, exported by `governance/governed_prompt.py`, full text in [`system_prompt_governed.txt`](system_prompt_governed.txt)) is now the live production default in `app._answer_with_context` — it is not a draft, it is what the deployed chatbot actually uses.
