"""Print model names only. Never print credentials or provider error bodies."""
import json
import os
import urllib.request
from engine.provider import load_env


def main():
    load_env()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in the ignored root .env first.")
    request = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": key})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
        for model in data.get("models", []):
            if "generateContent" in model.get("supportedGenerationMethods", []):
                print(model["name"].removeprefix("models/"))
    except Exception:
        raise SystemExit("Could not list models. Check the key, account access, and connection; no credentials were logged.") from None


if __name__ == "__main__":
    main()
