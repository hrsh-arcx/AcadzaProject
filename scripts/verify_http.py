"""Exercise the real deployed/local HTTP API in a new isolated demo workspace.

This makes test-only review actions, never student messages. No connection
string, session cookie, or signing secret is printed or written to disk.
"""
import argparse
import concurrent.futures
import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def verify(origin):
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "artifacts/cases.json").read_text(encoding="utf-8"))
    by_report = {r["reportId"]: c for c in cases for r in c["reports"]}
    cookie = None

    def call(method, body=None):
        headers = {"Origin": origin, "Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        request = urllib.request.Request(origin + "/api/workspace", data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.status, json.load(response), response.headers.get("Set-Cookie")
        except urllib.error.HTTPError as error:
            return error.code, json.load(error), None

    code, initial, set_cookie = call("GET")
    if code != 200:
        raise RuntimeError(f"Workspace GET failed with HTTP {code}; check database/session configuration")
    if initial["storage"] != "database":
        raise RuntimeError("Database is not configured; a browser sandbox is not database persistence evidence")
    cookie = set_cookie.split(";", 1)[0]
    assert initial["state"]["version"] == 0

    def proposal(report, action, version):
        c = by_report[report]
        return {"caseId": c["id"], "sourceHash": c["sourceHash"], "expectedVersion": version,
            "action": action, "reason": "Integration verification in an isolated demo workspace",
            "patches": c["patches"], "requestId": str(uuid.uuid4())}

    approval = proposal("R001", "approve", 0)
    code, first, _ = call("POST", approval)
    assert code == 200, f"Approval failed with HTTP {code}"
    review = first["state"]["reviews"][approval["caseId"]]
    assert review["status"] == "approved"
    assert review["question"][review["question"]["questionType"]]["answer"] == "A"
    code, refreshed, _ = call("GET")
    assert code == 200 and refreshed["state"] == first["state"], "Review did not survive a new GET"

    code, edited, _ = call("POST", proposal("R012", "edit", 1))
    assert code == 200 and edited["state"]["version"] == 2
    assert edited["state"]["reviews"][by_report["R012"]["id"]]["status"] == "draft"
    code, rejected, _ = call("POST", proposal("R034", "reject", 2))
    assert code == 200 and rejected["state"]["version"] == 3

    # Two writers use the same version. Exactly one may commit.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda body: call("POST", body), [proposal("R028", "approve", 3), proposal("R029", "approve", 3)]))
    assert sorted(x[0] for x in responses) == [200, 409], "Concurrent writes did not produce one winner and one conflict"
    code, final, _ = call("GET")
    assert code == 200 and final["state"]["version"] == 4 and len(final["state"]["audit"]) == 4
    code, retry, _ = call("POST", approval)
    assert code == 200 and retry["state"] == final["state"], "Idempotent retry created a duplicate event"
    print(json.dumps({"origin": origin, "storage": "database", "checks": ["approval", "persistence", "draft_edit", "rejection", "atomic_audit", "concurrent_conflict", "idempotency"], "passed": True, "auditEvents": 4}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="http://127.0.0.1:3100")
    args = parser.parse_args()
    verify(args.origin.rstrip("/"))
