import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
