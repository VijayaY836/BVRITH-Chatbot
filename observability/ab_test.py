"""Ex Obs-4: A/B test the grounding prompt (Prompt A = Day-4 baseline, Prompt B = stricter)."""
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

from app import BASE_GROUNDING_PROMPT, retrieve, _answer_with_context

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "data" / "ab_test_results.jsonl"
RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

PROMPT_A = BASE_GROUNDING_PROMPT
PROMPT_B = PROMPT_A + (
    "\n\n## STRICT MODE OVERRIDE\n"
    "Cite [Section, Page] for every fact. If the exact answer is not in the context, "
    "say 'I don't have that specific information.' Never infer or extrapolate."
)

# (question, is_answerable_from_the_kb) — the ground truth used to judge refusal correctness.
TEST_QUESTIONS = [
    ("What is the tuition fee for CSE?", True),
    ("What departments does BVRITH offer?", True),
    ("Who is the Chairman of the college?", True),
    ("What is the NAAC grade of BVRITH?", True),
    ("What was the highest placement package on record?", True),
    ("Tell me about the hostel facilities.", True),
    ("What is the weather in Hyderabad today?", False),
    ("Who is the President of the United States?", False),
    ("What is BVRITH's current stock price?", False),
    ("What is the capital of France?", False),
]


def assign_variant(query_id: str) -> str:
    """50/50 random assignment ('A' or 'B'). Logs the assignment via log_ab_result at call time."""
    return random.choice(["A", "B"])


def log_ab_result(query: str, variant: str, answer: str, had_citation: bool, refused: bool) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "variant": variant,
        "answer": answer,
        "had_citation": had_citation,
        "refused": refused,
    }
    with open(RESULTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _has_citation(answer: str) -> bool:
    return bool(re.search(r"\[[^\]]+,\s*Page\s*\d+\]", answer))


def _is_refusal(answer: str) -> bool:
    lowered = answer.lower()
    return any(p in lowered for p in [
        "don't have that", "do not have that", "not in the context",
        "don't have enough information", "do not have enough information",
        "i'm sorry, i don't have", "outside my knowledge",
    ])


def run_ab_test():
    """Runs all 10 fixed questions twice each (20 total), random A/B assignment per run."""
    results = {"A": [], "B": []}

    for question, in_kb in TEST_QUESTIONS:
        for _ in range(2):
            variant = assign_variant(question)
            base_prompt = PROMPT_A if variant == "A" else PROMPT_B
            retrieved = retrieve(question)
            answer, _ = _answer_with_context(question, retrieved, base_prompt=base_prompt)
            had_citation = _has_citation(answer)
            refused = _is_refusal(answer)
            log_ab_result(question, variant, answer, had_citation, refused)
            results[variant].append({
                "question": question, "in_kb": in_kb,
                "had_citation": had_citation, "refused": refused,
            })

    lines = ["# A/B Test Summary — Grounding Prompt (Prompt A vs Prompt B)", ""]
    for variant in ("A", "B"):
        runs = results[variant]
        n = len(runs) or 1
        citation_rate = 100 * sum(r["had_citation"] for r in runs) / n
        refusal_rate = 100 * sum(r["refused"] for r in runs) / n
        correct_refusals = sum(1 for r in runs if r["refused"] and not r["in_kb"])
        incorrect_refusals = sum(1 for r in runs if r["refused"] and r["in_kb"])
        lines += [
            f"## Variant {variant} ({len(runs)} runs)",
            f"- Citation rate: {citation_rate:.0f}%",
            f"- Refusal rate: {refusal_rate:.0f}%",
            f"- Correct refusals (question genuinely out-of-KB): {correct_refusals}",
            f"- Incorrect refusals (question was answerable, prompt was too strict): {incorrect_refusals}",
            "",
        ]

    summary_path = ROOT / "docs" / "ab_test_summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(TEST_QUESTIONS) * 2} records to {RESULTS_PATH}")
    print(f"Wrote summary to {summary_path}")
    return results


if __name__ == "__main__":
    run_ab_test()
