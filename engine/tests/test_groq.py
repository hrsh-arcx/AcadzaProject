import io
import json
import urllib.error

import pytest

from engine.models import Solve
from engine.provider import Groq, RequestTooLargeError, groq_retry_seconds


@pytest.fixture
def groq(monkeypatch, tmp_path):
    monkeypatch.setattr("engine.provider.load_env", lambda: None)
    monkeypatch.setenv("GROQ_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setenv("GROQ_REASONING_EFFORT", "low")
    return Groq(tmp_path, max_calls=2, min_interval=0)


def test_strict_schema_request_is_validated_and_cached(groq, monkeypatch):
    requests = []
    answer = {"answer": "A", "derivation": "Evidence", "assumptions": [], "sufficient_data": True}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    def respond(request, timeout):
        requests.append(request)
        body = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}
        return Response(json.dumps(body).encode())

    monkeypatch.setattr("engine.provider.urllib.request.urlopen", respond)
    assert groq.generate("solve-v1.txt", {"question": "test"}, Solve).answer == "A"
    sent = json.loads(requests[0].data)
    assert requests[0].full_url == "https://api.groq.com/openai/v1/chat/completions"
    assert sent["response_format"]["json_schema"]["strict"] is True
    assert sent["reasoning_effort"] == "low"
    assert "stored key" not in sent["messages"][1]["content"]
    assert groq.generate("solve-v1.txt", {"question": "test"}, Solve).answer == "A"
    assert groq.calls == 1 and groq.cache_hits == 1 and len(requests) == 1


def test_quota_does_not_spend_unbounded_retries(groq, monkeypatch):
    def limited(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://api.groq.com", 429, "Quota", {"retry-after": "3600"}, None)

    monkeypatch.setattr("engine.provider.urllib.request.urlopen", limited)
    with pytest.raises(RuntimeError, match="Groq HTTP 429"):
        groq.generate("solve-v1.txt", {"question": "test"}, Solve)
    assert groq.calls == 1


def test_oversized_request_is_typed_for_batch_splitting(groq, monkeypatch):
    def too_large(*_args, **_kwargs):
        raise urllib.error.HTTPError("https://api.groq.com", 413, "Too large", {}, None)

    monkeypatch.setattr("engine.provider.urllib.request.urlopen", too_large)
    with pytest.raises(RequestTooLargeError):
        groq.generate("solve-v1.txt", {"question": "test"}, Solve)
    assert groq.calls == 1


def test_schema_generation_error_gets_one_bounded_retry(groq, monkeypatch):
    attempts = []
    answer = {"answer": "A", "derivation": "Evidence", "assumptions": [], "sufficient_data": True}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    def respond(*_args, **_kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            body = io.BytesIO(json.dumps({"error": {"message": "Generated JSON does not match schema"}}).encode())
            raise urllib.error.HTTPError("https://api.groq.com", 400, "Bad request", {}, body)
        return Response(json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}).encode())

    monkeypatch.setattr("engine.provider.urllib.request.urlopen", respond)
    monkeypatch.setattr("engine.provider.time.sleep", lambda *_: None)
    assert groq.generate("solve-v1.txt", {"question": "test"}, Solve).answer == "A"
    assert groq.calls == 2 and len(attempts) == 2


def test_missing_key_fails_before_any_request(monkeypatch, tmp_path):
    monkeypatch.setattr("engine.provider.load_env", lambda: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        Groq(tmp_path)


def test_retry_delay_parses_groq_rate_limit_units():
    assert groq_retry_seconds("67.5ms") == pytest.approx(.0675)
    assert groq_retry_seconds("12s") == 12
    assert groq_retry_seconds("1.5m") == 90
    assert groq_retry_seconds("7") == 7
    assert groq_retry_seconds("unknown") is None


def test_repeated_schema_failure_uses_validated_json_object_fallback(groq, monkeypatch):
    groq.max_calls = 3
    modes = []
    answer = {"answer": "A", "derivation": "Evidence", "assumptions": [], "sufficient_data": True}

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    def respond(request, timeout):
        mode = json.loads(request.data)["response_format"]["type"]
        modes.append(mode)
        if mode == "json_schema":
            body = io.BytesIO(json.dumps({"error": {"message": "Generated JSON does not match schema"}}).encode())
            raise urllib.error.HTTPError("https://api.groq.com", 400, "Bad request", {}, body)
        return Response(json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}).encode())

    monkeypatch.setattr("engine.provider.urllib.request.urlopen", respond)
    monkeypatch.setattr("engine.provider.time.sleep", lambda *_: None)
    assert groq.generate("solve-v1.txt", {"question": "test"}, Solve).answer == "A"
    assert modes == ["json_schema", "json_schema", "json_object"]
    assert groq.response_modes == {"json_object"}
    assert groq.generate("solve-v1.txt", {"question": "test"}, Solve).answer == "A"
    assert groq.calls == 3 and groq.cache_hits == 1


def test_minute_limit_waits_but_daily_limit_stops(groq, monkeypatch):
    answer = {"answer": "A", "derivation": "Evidence", "assumptions": [], "sufficient_data": True}
    waits = []
    attempts = []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    def respond(*_args, **_kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            body = io.BytesIO(json.dumps({"error": {"message": "TPM Limit 8000"}}).encode())
            raise urllib.error.HTTPError("https://api.groq.com", 429, "Rate", {"retry-after": "2"}, body)
        return Response(json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}]}).encode())

    monkeypatch.setattr("engine.provider.urllib.request.urlopen", respond)
    monkeypatch.setattr("engine.provider.time.sleep", waits.append)
    assert groq.generate("solve-v1.txt", {"question": "test"}, Solve).answer == "A"
    assert waits == [3] and groq.calls == 2

    groq.max_calls = 3
    def daily(*_args, **_kwargs):
        body = io.BytesIO(json.dumps({"error": {"message": "TPD Limit 200000"}}).encode())
        raise urllib.error.HTTPError("https://api.groq.com", 429, "Rate", {"retry-after": "2"}, body)
    monkeypatch.setattr("engine.provider.urllib.request.urlopen", daily)
    with pytest.raises(RuntimeError, match="daily limit reached"):
        groq.generate("verify-v1.txt", {"question": "different"}, Solve)
    assert groq.calls == 3 and waits == [3]
