import json
import urllib.error
import pytest
from engine.models import Solve
from engine.provider import Gemini


@pytest.fixture
def provider(monkeypatch, tmp_path):
    monkeypatch.setattr("engine.provider.load_env", lambda: None)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    return Gemini(tmp_path, max_calls=1, min_interval=0)


def test_request_budget_cannot_be_exceeded(provider):
    provider.reserve_request()
    with pytest.raises(RuntimeError, match="budget reached"):
        provider.reserve_request()
    assert provider.calls == 1


def test_cached_result_uses_no_request_budget(provider):
    prompt = "solve-v1.txt"
    from engine.provider import ROOT
    import hashlib
    data = {"question": "test"}
    body = {"systemInstruction": {"parts": [{"text": (ROOT / "engine/prompts" / prompt).read_text(encoding="utf-8")}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(data, ensure_ascii=False)}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": Solve.model_json_schema()}}
    key = hashlib.sha256(json.dumps([provider.model, body], sort_keys=True).encode()).hexdigest()
    answer = {"answer": "A", "derivation": "test cached response", "assumptions": [], "sufficient_data": True}
    (provider.directory / (key + ".json")).write_text(json.dumps({"parsed": answer}), encoding="utf-8")
    provider.max_calls = 0
    assert provider.generate(prompt, data, Solve).answer == "A"
    assert provider.calls == 0 and provider.cache_hits == 1


def test_quota_error_stops_after_one_attempt(provider, monkeypatch):
    attempts = []
    def quota(request, timeout):
        attempts.append(1)
        raise urllib.error.HTTPError("https://example.invalid", 429, "Quota", {}, None)
    monkeypatch.setattr("engine.provider.urllib.request.urlopen", quota)
    with pytest.raises(RuntimeError, match="HTTP 429"):
        provider.generate("solve-v1.txt", {"question": "test"}, Solve)
    assert len(attempts) == 1
    assert provider.calls == 1


def test_pacing_is_between_actual_requests(provider, monkeypatch):
    provider.max_calls = 2
    provider.min_interval = 12
    clock = iter([100, 104, 112])
    sleeps = []
    monkeypatch.setattr("engine.provider.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("engine.provider.time.sleep", sleeps.append)
    provider.reserve_request()
    provider.reserve_request()
    assert sleeps == [8]
