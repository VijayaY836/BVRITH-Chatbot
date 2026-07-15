"""Acceptance tests for the Observability layer (spec.MD section 4)."""
import json
from pathlib import Path
from types import SimpleNamespace

from observability.alerts import THRESHOLDS, check_alerts, validate_input_length
from observability.logger import LOG_PATH, VALID_CALL_TYPES, logged_llm_call
from observability.metrics import EMPTY_STATS, compute_session_stats

ROOT = Path(__file__).resolve().parent.parent

# Directories that legitimately never call an LLM directly and shouldn't be scanned
# (virtualenvs, caches, generated data).
_SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "chroma_db", "images", "scraped_pages"}


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content, prompt_tokens=10, completion_tokens=5):
        self.choices = [_FakeChoice(content)]
        self.usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)


class _FakeCompletions:
    def __init__(self, content=None, raise_error=False):
        self._content = content
        self._raise_error = raise_error

    def create(self, model, messages, **kwargs):
        if self._raise_error:
            raise RuntimeError("simulated API failure")
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, **kwargs):
        self.completions = _FakeCompletions(**kwargs)


class _FakeClient:
    def __init__(self, **kwargs):
        self.chat = _FakeChat(**kwargs)


# ── ✓ 6.2 Logging discipline: no raw LLM call outside observability/logger.py ────

def test_no_raw_llm_calls_outside_logger():
    # Files exempt from the scan: the wrapper itself (defines the real call), and this
    # test file (its source contains the search pattern as a string literal).
    exempt = {(ROOT / "observability" / "logger.py").resolve(),
              (ROOT / "tests" / "test_observability.py").resolve()}
    offenders = []
    for py_file in ROOT.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in py_file.parts):
            continue
        if py_file.resolve() in exempt:
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if "chat.completions.create(" in text:
            offenders.append(str(py_file.relative_to(ROOT)))
    assert offenders == [], f"Raw LLM calls found outside logged_llm_call: {offenders}"


# ── Ex Obs-1: logged_llm_call shape ─────────────────────────────────────────────

def test_logged_llm_call_success_shape():
    client = _FakeClient(content="hello world")
    result = logged_llm_call(
        model="openai/gpt-4o-mini", messages=[{"role": "user", "content": "hi"}],
        call_type="rag_generation", llm_client=client,
    )
    assert result["content"] == "hello world"
    entry = result["log_entry"]
    for field in ("timestamp", "call_type", "model", "input_tokens", "output_tokens",
                  "latency_ms", "estimated_cost_usd", "status", "error"):
        assert field in entry
    assert entry["status"] == "success"
    assert entry["error"] is None
    assert entry["input_tokens"] == 10 and entry["output_tokens"] == 5


def test_logged_llm_call_failure_shape():
    client = _FakeClient(raise_error=True)
    result = logged_llm_call(
        model="openai/gpt-4o-mini", messages=[{"role": "user", "content": "hi"}],
        call_type="rag_generation", llm_client=client,
    )
    assert result["content"] is None
    assert result["log_entry"]["status"] == "failure"
    assert result["log_entry"]["error"] is not None


def test_logged_llm_call_rejects_unknown_call_type():
    client = _FakeClient(content="x")
    try:
        logged_llm_call(model="m", messages=[], call_type="not_a_real_type", llm_client=client)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_logged_llm_call_appends_to_jsonl(tmp_path, monkeypatch):
    fake_log = tmp_path / "llm_calls.jsonl"
    monkeypatch.setattr("observability.logger.LOG_PATH", fake_log)
    client = _FakeClient(content="ok")
    logged_llm_call(model="openai/gpt-4o-mini", messages=[{"role": "user", "content": "hi"}],
                     call_type="rag_generation", llm_client=client)
    lines = fake_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["status"] == "success"


# ── Ex Obs-2: session stats ─────────────────────────────────────────────────────

def test_compute_session_stats_empty():
    assert compute_session_stats([]) == EMPTY_STATS


def test_compute_session_stats_aggregates():
    call_log = [
        {"call_type": "rag_generation", "latency_ms": 1000, "estimated_cost_usd": 0.01,
         "input_tokens": 100, "output_tokens": 50, "status": "success"},
        {"call_type": "rag_generation", "latency_ms": 2000, "estimated_cost_usd": 0.02,
         "input_tokens": 200, "output_tokens": 60, "status": "failure"},
        {"call_type": "summarization", "latency_ms": 500, "estimated_cost_usd": 0.005,
         "input_tokens": 300, "output_tokens": 40, "status": "success"},
    ]
    stats = compute_session_stats(call_log)
    assert stats["total_queries"] == 2  # only rag_generation calls
    assert stats["error_count"] == 1
    assert stats["total_tokens"] == 100 + 50 + 200 + 60 + 300 + 40
    assert stats["avg_latency_s"] == round((1.0 + 2.0 + 0.5) / 3, 3)


# ── Ex Obs-3: alerts + input validation ─────────────────────────────────────────

def test_validate_input_length_rejects_overlong():
    is_valid, message = validate_input_length("x" * 2001, max_chars=2000)
    assert not is_valid
    assert message is not None


def test_validate_input_length_accepts_normal():
    is_valid, message = validate_input_length("What is the CSE fee?", max_chars=2000)
    assert is_valid
    assert message is None


def test_check_alerts_latency_breach():
    call_log = [{"latency_ms": (THRESHOLDS["latency_s"] + 1) * 1000, "call_type": "rag_generation",
                 "estimated_cost_usd": 0.001, "status": "success"}]
    warnings = check_alerts(call_log)
    assert any("Latency" in w for w in warnings)


def test_check_alerts_error_rate_breach():
    window = [{"latency_ms": 100, "call_type": "rag_generation", "estimated_cost_usd": 0.001,
               "status": "failure" if i < 2 else "success"} for i in range(20)]
    warnings = check_alerts(window)
    assert any("Error rate" in w for w in warnings)


def test_check_alerts_no_warnings_when_healthy():
    call_log = [{"latency_ms": 500, "call_type": "rag_generation", "estimated_cost_usd": 0.001,
                 "status": "success"}]
    assert check_alerts(call_log) == []
