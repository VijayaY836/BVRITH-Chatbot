import json
import sys
import time
from pathlib import Path

import streamlit as st

# Import eval logic directly
from evaluate import run_evaluation

ROOT = Path(__file__).resolve().parent

DIMENSION_COLORS = {
    "Functional": "#4C9BE8",
    "Quality": "#A78BFA",
    "Safety": "#34D399",
    "Security": "#F87171",
    "Robustness": "#FBBF24",
    "Performance": "#60A5FA",
    "Context": "#F472B6",
    "RAGAS": "#2DD4BF",
}

DIMENSION_ICONS = {
    "Functional": "⚙️",
    "Quality": "✨",
    "Safety": "🛡️",
    "Security": "🔒",
    "Robustness": "💪",
    "Performance": "⚡",
    "Context": "🧠",
    "RAGAS": "📊",
}

st.set_page_config(
    page_title="BVRIT Chatbot Evaluator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #f8f9fc; }
[data-testid="stSidebar"] { background: #f0f2f8; }

.metric-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #e2e5ef;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.metric-card .value {
    font-size: 2.4rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
}
.metric-card .label {
    font-size: 0.78rem;
    color: #8b92a8;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.dim-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 16px 20px;
    border: 1px solid #e2e5ef;
    margin-bottom: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.dim-card .dim-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 8px;
}
.dim-bar-bg {
    background: #e8eaf2;
    border-radius: 100px;
    height: 8px;
    width: 100%;
}
.dim-bar-fill {
    border-radius: 100px;
    height: 8px;
}

.result-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 16px 20px;
    border-left: 4px solid;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.result-card.pass { border-color: #16a34a; }
.result-card.fail { border-color: #dc2626; }

.ragas-bar-label {
    font-size: 0.82rem;
    color: #8b92a8;
    margin-bottom: 4px;
}
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.badge-pass { background: #dcfce7; color: #16a34a; }
.badge-fail { background: #fee2e2; color: #dc2626; }

.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1e2235;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e2e5ef;
}
.warning-box {
    background: #fffbeb;
    border: 1px solid #d97706;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.82rem;
    color: #92400e;
}
.fix-box {
    background: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 0.85rem;
    color: #1d4ed8;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_report():
    return st.session_state.get("report", None)


def score_color(rate: float) -> str:
    if rate >= 80:
        return "#16a34a"
    elif rate >= 50:
        return "#d97706"
    return "#dc2626"


def ragas_color(score: float) -> str:
    if score >= 0.85:
        return "#16a34a"
    elif score >= 0.6:
        return "#d97706"
    return "#dc2626"


# ── Sidebar ─────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 Evaluation Dashboard")
    st.markdown("---")

    report = load_report()

    if report:
        ts_text = f"Last run · {report['summary']['total_cases']} cases"
        st.markdown(f"<div style='font-size:0.78rem;color:#8b92a8;margin-bottom:16px'>{ts_text}</div>",
                    unsafe_allow_html=True)

    st.markdown("### Run Evaluation")
    st.markdown(
        "<div style='font-size:0.82rem;color:#8b92a8;margin-bottom:12px'>"
        "Runs all test cases against the live chatbot and re-generates the report."
        "</div>",
        unsafe_allow_html=True,
    )

    if "eval_running" not in st.session_state:
        st.session_state.eval_running = False
    if "report" not in st.session_state:
        st.session_state.report = None

    run_btn = st.button(
        "▶  Run Evaluation" if not st.session_state.eval_running else "⏳  Running...",
        use_container_width=True,
        disabled=st.session_state.eval_running,
        type="primary",
    )

    if run_btn and not st.session_state.eval_running:
        st.session_state.eval_running = True
        st.session_state.report = None
        st.rerun()

    if st.session_state.eval_running:
        with st.spinner("Evaluation in progress…"):
            try:
                report_data = run_evaluation()
                st.session_state.report = report_data
            except Exception as e:
                st.error(f"Evaluation failed: {e}")
                st.session_state.report = None
        st.session_state.eval_running = False
        st.rerun()

    st.markdown("---")
    st.markdown("### Filters")
    dim_filter = st.multiselect(
        "Dimensions",
        options=list(DIMENSION_ICONS.keys()),
        default=[],
        placeholder="All dimensions",
    )
    pass_filter = st.selectbox("Result", ["All", "Passed", "Failed"], index=0)


# ── Main ────────────────────────────────────────────────────────────────────────

report = load_report()

if not report and not st.session_state.get("eval_running", False):
    st.markdown(
        "<div style='text-align:center;padding:80px 0;color:#8b92a8'>"
        "<div style='font-size:3rem;margin-bottom:16px'>📭</div>"
        "<div style='font-size:1.1rem;font-weight:600;color:#1e2235;margin-bottom:8px'>No report yet</div>"
        "<div style='font-size:0.88rem'>Click <strong>Run Evaluation</strong> in the sidebar to generate one.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

if not report:
    st.stop()  # eval is running, sidebar handles the spinner

summary = report["summary"]
dim_breakdown = report["per_dimension_breakdown"]
ragas_scores = report.get("ragas_scores", {})
results = report.get("results", [])

# ── Page title ──────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='font-size:1.8rem;font-weight:700;margin-bottom:4px;color:#1e2235'>BVRIT Chatbot · Evaluation Report</h1>"
    "<p style='color:#8b92a8;font-size:0.88rem;margin-bottom:32px'>LLM-as-judge · Automated RAG evaluation</p>",
    unsafe_allow_html=True,
)

# ── Top metrics ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
pass_rate = summary["overall_pass_rate"]
pr_color = score_color(pass_rate)

with c1:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='value' style='color:{pr_color}'>{pass_rate}%</div>"
        f"<div class='label'>Overall Pass Rate</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='value' style='color:#16a34a'>{summary['passed']}</div>"
        f"<div class='label'>Passed</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='value' style='color:#dc2626'>{summary['failed']}</div>"
        f"<div class='label'>Failed</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"<div class='metric-card'>"
        f"<div class='value' style='color:#7c3aed'>{summary['total_cases']}</div>"
        f"<div class='label'>Total Cases</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── Two-column layout: Dimension breakdown + RAGAS ──────────────────────────────
left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown("<div class='section-header'>Dimension Breakdown</div>", unsafe_allow_html=True)
    for dim, counts in dim_breakdown.items():
        total = counts["passed"] + counts["failed"]
        rate = (counts["passed"] / total * 100) if total else 0
        color = DIMENSION_COLORS.get(dim, "#8b8fa8")
        icon = DIMENSION_ICONS.get(dim, "•")
        bar_width = int(rate)
        st.markdown(
            f"""
            <div class='dim-card'>
                <div class='dim-title' style='color:{color}'>{icon} {dim}</div>
                <div style='display:flex;justify-content:space-between;font-size:0.8rem;color:#8b92a8;margin-bottom:6px'>
                    <span>{counts['passed']}/{total} passed</span>
                    <span style='color:{score_color(rate)};font-weight:600'>{rate:.0f}%</span>
                </div>
                <div class='dim-bar-bg'>
                    <div class='dim-bar-fill' style='width:{bar_width}%;background:{color}'></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with right:
    st.markdown("<div class='section-header'>RAGAS Scores</div>", unsafe_allow_html=True)

    ragas_labels = {
        "faithfulness": ("Faithfulness", "🎯"),
        "answer_relevancy": ("Answer Relevancy", "💬"),
        "context_precision": ("Context Precision", "🔍"),
        "context_recall": ("Context Recall", "📚"),
    }

    for key, (label, icon) in ragas_labels.items():
        score = ragas_scores.get(key, 0)
        pct = int(score * 100)
        color = ragas_color(score)
        st.markdown(
            f"""
            <div style='margin-bottom:20px'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:5px'>
                    <span style='font-size:0.88rem;color:#4b5563'>{icon} {label}</span>
                    <span style='font-size:1.05rem;font-weight:700;color:{color}'>{score:.4f}</span>
                </div>
                <div class='dim-bar-bg'>
                    <div class='dim-bar-fill' style='width:{pct}%;background:{color}'></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    weakest = report.get("weakest_dimension", "")
    weakest_rate = report.get("weakest_dimension_pass_rate", 0)
    overall_rate = report.get("summary", {}).get("overall_pass_rate", 0)
    if weakest and weakest_rate < 100:
        w_color = DIMENSION_COLORS.get(weakest, "#8b8fa8")
        w_icon = DIMENSION_ICONS.get(weakest, "•")
        st.markdown(
            f"<div style='background:#ffffff;border-radius:10px;padding:14px 18px;border:1px solid #e2e5ef;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,0.04)'>"
            f"<div style='font-size:0.75rem;color:#8b92a8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px'>Weakest Dimension</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{w_color}'>{w_icon} {weakest} · {weakest_rate}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif overall_rate == 100.0:
        st.markdown(
            "<div style='background:#f0fdf4;border-radius:10px;padding:14px 18px;border:1px solid #bbf7d0;margin-bottom:10px'>"
            "<div style='font-size:0.75rem;color:#16a34a;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px'>All Dimensions</div>"
            "<div style='font-size:1rem;font-weight:700;color:#16a34a'>🎉 100% across the board</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    fix = report.get("recommended_fix", "")
    if fix:
        st.markdown(
            f"<div class='fix-box'>💡 <strong>Recommended fix:</strong> {fix}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── RAGAS diagnosis ────────────────────────────────────────────────────────────
ragas_diag = report.get("ragas_diagnosis", "")
lowest_ragas = min(report.get("ragas_scores", {}).values()) if report.get("ragas_scores") else 1.0
if ragas_diag and lowest_ragas < 0.95:
    st.markdown(
        f"<div class='warning-box'>⚠️ {ragas_diag}</div>",
        unsafe_allow_html=True,
    )
elif lowest_ragas >= 0.95:
    st.markdown(
        "<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px 16px;font-size:0.82rem;color:#16a34a'>"
        "✅ All RAGAS metrics are strong (≥ 0.95). No action needed."
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ── Per-result cards ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Test Results</div>", unsafe_allow_html=True)

# Apply filters
filtered = results
if dim_filter:
    filtered = [r for r in filtered if r["dimension"] in dim_filter]
if pass_filter == "Passed":
    filtered = [r for r in filtered if r["pass"]]
elif pass_filter == "Failed":
    filtered = [r for r in filtered if not r["pass"]]

# Group by dimension
grouped: dict = {}
for r in filtered:
    grouped.setdefault(r["dimension"], []).append(r)

if not filtered:
    st.markdown(
        "<div style='text-align:center;padding:40px;color:#8b92a8;font-size:0.9rem'>No results match the current filters.</div>",
        unsafe_allow_html=True,
    )
else:
    for dim, cases in grouped.items():
        color = DIMENSION_COLORS.get(dim, "#8b8fa8")
        icon = DIMENSION_ICONS.get(dim, "•")
        passed_count = sum(1 for c in cases if c["pass"])
        with st.expander(f"{icon} {dim}  ·  {passed_count}/{len(cases)} passed", expanded=(dim_filter != [])):
            for case in cases:
                is_pass = case["pass"]
                status_cls = "pass" if is_pass else "fail"
                badge_cls = "badge-pass" if is_pass else "badge-fail"
                badge_text = "PASS" if is_pass else "FAIL"
                latency = case.get("latency_seconds", 0)
                chunks = case.get("retrieved_chunks", [])
                dim_color = DIMENSION_COLORS.get(dim, "#8b8fa8")

                st.markdown(
                    f"""
                    <div class='result-card {status_cls}'>
                        <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px'>
                            <div style='font-size:0.95rem;font-weight:600;color:#1e2235;flex:1;padding-right:12px'>{case['question'] or "<em style='color:#8b92a8'>empty input</em>"}</div>
                            <div style='display:flex;gap:8px;align-items:center;white-space:nowrap'>
                                <span style='font-size:0.78rem;color:#8b92a8'>⏱ {latency:.2f}s</span>
                                <span class='badge {badge_cls}'>{badge_text}</span>
                            </div>
                        </div>
                        <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px'>
                            <div>
                                <div style='font-size:0.72rem;color:#8b92a8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px'>Expected</div>
                                <div style='font-size:0.83rem;color:#166534;background:#f0fdf4;padding:8px 10px;border-radius:6px;border:1px solid #bbf7d0'>{case['expected_answer']}</div>
                            </div>
                            <div>
                                <div style='font-size:0.72rem;color:#8b92a8;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px'>Actual</div>
                                <div style='font-size:0.83rem;color:#374151;background:#f8f9fc;padding:8px 10px;border-radius:6px;border:1px solid #e2e5ef;max-height:120px;overflow-y:auto'>{case['actual_response'][:400]}{"…" if len(case["actual_response"]) > 400 else ""}</div>
                            </div>
                        </div>
                        <div style='display:flex;justify-content:space-between;align-items:flex-end'>
                            <div style='font-size:0.8rem;color:#6b7280'><strong style='color:#4b5563'>Judge:</strong> {case['reason']}</div>
                        </div>
                        {"<div style='margin-top:8px;display:flex;flex-wrap:wrap;gap:6px'>" + "".join(f"<span style='font-size:0.72rem;padding:2px 8px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:100px;color:#1d4ed8'>{c}</span>" for c in chunks) + "</div>" if chunks else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;font-size:0.75rem;color:#9ca3af'>"
    "Automated LLM-as-judge evaluation · Manual review recommended for confirmation"
    "</div>",
    unsafe_allow_html=True,
)
