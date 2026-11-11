"""Print model names only. Never print credentials or provider error bodies."""
import json
import os
import urllib.request
from engine.provider import load_env


def main():
    load_env()
    groq_key = os.environ.get("GROQ_API_KEY")
    key = groq_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Set GROQ_API_KEY or GEMINI_API_KEY in the ignored root .env first.")
    request = (urllib.request.Request("https://api.groq.com/openai/v1/models", headers={
        "Authorization": f"Bearer {key}", "User-Agent": "AcadzaTriage/1.0 (Python urllib)"})
        if groq_key else urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": key}))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        if groq_key:
            for model in sorted(data.get("data", []), key=lambda item: item["id"]):
                if model.get("active", True):
                    print(model["id"])
        else:
            for model in data.get("models", []):
                if "generateContent" in model.get("supportedGenerationMethods", []):
                    print(model["name"].removeprefix("models/"))
    except Exception:
        raise SystemExit("Could not list models. Check the key, account access, and connection; no credentials were logged.") from None


if __name__ == "__main__":
    main()
