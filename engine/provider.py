import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RequestTooLargeError(RuntimeError):
    """The provider rejected a request body; callers may split a batch."""


def groq_retry_seconds(value):
    if value is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(ms|s|m)?\s*", str(value), re.I)
    if not match:
        return None
    amount = float(match.group(1))
    return amount * {"ms": .001, "s": 1, "m": 60}[match.group(2).lower() if match.group(2) else "s"]


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


class Gemini:
    def __init__(self, directory, max_calls=120, min_interval=12):
        load_env()
        self.key = os.environ.get("GEMINI_API_KEY")
        self.model = os.environ.get("GEMINI_MODEL")
        if not self.key or not self.model:
            raise ValueError("Set GEMINI_API_KEY and GEMINI_MODEL in the ignored root .env; no live results were generated.")
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", self.model):
            raise ValueError("Invalid model identifier")
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        self.cache_hits = 0
        self.max_calls = max_calls
        self.min_interval = min_interval
        self.last_request = None
        self.thinking_level = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower()
        if self.thinking_level and self.thinking_level not in ("low", "medium", "high"):
            raise ValueError("GEMINI_THINKING_LEVEL must be low, medium, high, or blank")
        self.timeout = 180

    def reserve_request(self):
        if self.calls >= self.max_calls:
            raise RuntimeError("Per-run request budget reached; cached progress is preserved")
        if self.last_request is not None:
            delay = self.min_interval - (time.monotonic() - self.last_request)
            if delay > 0:
                time.sleep(delay)
        self.calls += 1
        self.last_request = time.monotonic()

    def generate(self, prompt_file, data, model):
        prompt = (ROOT / "engine/prompts" / prompt_file).read_text(encoding="utf-8")
        request_body = {"systemInstruction": {"parts": [{"text": prompt}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(data, ensure_ascii=False)}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": model.model_json_schema()}}
        if self.thinking_level:
            request_body["generationConfig"]["thinkingConfig"] = {"thinkingLevel": self.thinking_level}
        cache_key = hashlib.sha256(json.dumps([self.model, request_body], sort_keys=True).encode()).hexdigest()
        cache = self.directory / (cache_key + ".json")
        if cache.exists():
            self.cache_hits += 1
            return model.model_validate(json.loads(cache.read_text(encoding="utf-8"))["parsed"])
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            data=json.dumps(request_body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.key}, method="POST")
        for attempt in range(3):
            try:
                self.reserve_request()
                print(f"Gemini request {self.calls}/{self.max_calls}: {prompt_file}", flush=True)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = json.load(response)
                candidate = raw.get("candidates", [{}])[0]
                if candidate.get("finishReason") != "STOP":
                    raise ValueError("Gemini refused or truncated its response; run stopped without replacing results.json")
                body = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", []) if not part.get("thought"))
                parsed = model.model_validate_json(body)
                cache.write_text(json.dumps({"model": self.model, "request": request_body,
                    "parsed": parsed.model_dump(), "usage": raw.get("usageMetadata"), "response": raw}, ensure_ascii=False, indent=2), encoding="utf-8")
                return parsed
            except urllib.error.HTTPError as error:
                # Never print request headers, keys, or provider response bodies.
                # A free-tier quota error stops immediately; do not spend retries
                # guessing whether a daily quota or a per-minute quota was hit.
                quota = []
                if error.code == 429:
                    try:
                        details = json.loads(error.read()).get("error", {}).get("details", [])
                        for detail in details:
                            for violation in detail.get("violations", []):
                                quota.append({k: violation[k] for k in ("quotaMetric", "quotaId", "quotaValue") if k in violation})
                            if detail.get("retryDelay"):
                                quota.append({"retryDelay": detail["retryDelay"]})
                    except (ValueError, OSError):
                        pass
                if error.code not in (500, 502, 503, 504) or attempt == 2:
                    suffix = "; quota details=" + json.dumps(quota) if quota else ""
                    raise RuntimeError(f"Gemini HTTP {error.code}; no credentials logged, existing results preserved{suffix}") from None
                time.sleep(2 ** attempt)
        raise RuntimeError("Provider retries exhausted")


class Groq(Gemini):
    """Groq Chat Completions adapter with the same budget and cache contract."""

    def __init__(self, directory, max_calls=45, min_interval=20):
        load_env()
        self.key = os.environ.get("GROQ_API_KEY")
        self.model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        if not self.key:
            raise ValueError("Set GROQ_API_KEY in the ignored root .env; no live results were generated.")
        if not re.fullmatch(r"[a-zA-Z0-9._/-]+", self.model):
            raise ValueError("Invalid model identifier")
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        self.cache_hits = 0
        self.max_calls = max_calls
        self.min_interval = min_interval
        self.last_request = None
        self.thinking_level = os.environ.get("GROQ_REASONING_EFFORT", "low").strip().lower()
        self.response_modes = set()
        if self.thinking_level not in ("low", "medium", "high", ""):
            raise ValueError("GROQ_REASONING_EFFORT must be low, medium, high, or blank")
        self.timeout = 180

    def generate(self, prompt_file, data, model, _json_fallback=False):
        prompt = (ROOT / "engine/prompts" / prompt_file).read_text(encoding="utf-8")
        if _json_fallback:
            prompt += "\n" + (ROOT / "engine/prompts/json-fallback.txt").read_text(encoding="utf-8")
            prompt += "\nJSON Schema:\n" + json.dumps(model.model_json_schema(), ensure_ascii=False)
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
            ],
            "response_format": ({"type": "json_object"} if _json_fallback else
                {"type": "json_schema", "json_schema": {
                    "name": model.__name__, "strict": True, "schema": model.model_json_schema()}}),
        }
        if self.thinking_level:
            request_body["reasoning_effort"] = self.thinking_level
        cache_key = hashlib.sha256(json.dumps([self.model, request_body], sort_keys=True).encode()).hexdigest()
        cache = self.directory / (cache_key + ".json")
        fallback_marker = self.directory / (cache_key + ".fallback")
        if cache.exists():
            self.cache_hits += 1
            self.response_modes.add("json_object" if _json_fallback else "strict_json_schema")
            return model.model_validate(json.loads(cache.read_text(encoding="utf-8"))["parsed"])
        if not _json_fallback and fallback_marker.exists():
            return self.generate(prompt_file, data, model, _json_fallback=True)
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(request_body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}",
                     "User-Agent": "AcadzaTriage/1.0 (Python urllib)"},
            method="POST")
        for attempt in range(3):
            try:
                self.reserve_request()
                print(f"Groq request {self.calls}/{self.max_calls}: {prompt_file}", flush=True)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = json.load(response)
                choice = raw.get("choices", [{}])[0]
                message = choice.get("message", {})
                if choice.get("finish_reason") != "stop" or message.get("refusal"):
                    raise ValueError("Groq refused or truncated its response; run stopped without replacing results.json")
                parsed = model.model_validate_json(message.get("content") or "")
                cache.write_text(json.dumps({"model": self.model, "request": request_body,
                    "parsed": parsed.model_dump(), "usage": raw.get("usage"), "response": raw},
                    ensure_ascii=False, indent=2), encoding="utf-8")
                self.response_modes.add("json_object" if _json_fallback else "strict_json_schema")
                return parsed
            except urllib.error.HTTPError as error:
                # Never print raw provider error bodies or authorization headers.
                if error.code == 413:
                    raise RequestTooLargeError("Groq HTTP 413; request must be split, existing results preserved") from None
                if error.code == 429:
                    try:
                        rate_message = str(json.loads(error.read()).get("error", {}).get("message", ""))
                    except (ValueError, OSError):
                        rate_message = ""
                    rate_match = re.search(r"\b(TPM|TPD|RPM|RPD)\b", rate_message)
                    rate_type = rate_match.group(1) if rate_match else "unknown"
                    if rate_type in ("TPD", "RPD"):
                        raise RuntimeError(f"Groq HTTP 429 ({rate_type}); daily limit reached, existing results preserved") from None
                    delay = groq_retry_seconds(error.headers.get("retry-after") if error.headers else None)
                    if delay is None and error.headers:
                        delay = groq_retry_seconds(error.headers.get("x-ratelimit-reset-tokens"))
                    if delay is None:
                        match = re.search(r"Please try again in\s+([\d.]+\s*(?:ms|s|m))", rate_message, re.I)
                        delay = groq_retry_seconds(match.group(1)) if match else None
                    if delay is not None and 0 < delay <= 180 and attempt < 2 and self.calls < self.max_calls:
                        time.sleep(delay + 1)
                        continue
                    raise RuntimeError(f"Groq HTTP 429 ({rate_type}); rate limit, existing results preserved") from None
                if error.code in (500, 502, 503, 504) and attempt < 2 and self.calls < self.max_calls:
                    time.sleep(2 ** attempt)
                    continue
                category = ""
                if error.code == 400:
                    try:
                        detail = json.loads(error.read()).get("error", {})
                        message = str(detail.get("message", "")).lower()
                        category = "schema_or_json" if "json" in message or "schema" in message else "context" if "context" in message else "other"
                    except (ValueError, OSError):
                        category = "non_json_error"
                if category == "schema_or_json" and attempt == 0 and self.calls < self.max_calls:
                    time.sleep(2 ** attempt)
                    continue
                if category == "schema_or_json" and not _json_fallback and self.calls < self.max_calls:
                    parsed = self.generate(prompt_file, data, model, _json_fallback=True)
                    fallback_marker.write_text("json_object\n", encoding="ascii")
                    return parsed
                suffix = f" ({category})" if category else ""
                raise RuntimeError(f"Groq HTTP {error.code}{suffix}; no credentials logged, existing results preserved") from None
        raise RuntimeError("Groq retries exhausted")
