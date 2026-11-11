"""Compare the complete live candidate with the displayed reviewed snapshot."""

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.cli import load_data, validate_export
from engine.content import digest


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    baseline = read("results.json")
    live = read("artifacts/live/results.json")
    cases = read("artifacts/live/cases.json")
    manifest = read("artifacts/live/manifest.json")
    questions, reports, taxonomy = load_data()
    validate_export(baseline, questions, reports, taxonomy)
    validate_export(live, questions, reports, taxonomy)
    if not manifest["complete"] or manifest["resultsHash"] != digest(live):
        raise ValueError("Only an intact, complete live candidate can be compared")
    reviewed = {row["reportId"]: row for row in baseline}
    agreement = [row["reportId"] for row in live if
        (row["verdict"], row["repair"]) == (reviewed[row["reportId"]]["verdict"], reviewed[row["reportId"]]["repair"])]
    route_diffs = [row["reportId"] for row in live if row["route"] != reviewed[row["reportId"]]["route"]]
    edit_diffs = [row["reportId"] for row in live if row["edit"] != reviewed[row["reportId"]]["edit"]]
    comparison = {
        "comparedAt": datetime.now(timezone.utc).isoformat(),
        "baselineResultsHash": digest(baseline),
        "liveResultsHash": digest(live),
        "reportCount": len(live),
        "groupedCases": len(cases),
        "verdictRepairAgreement": len(agreement),
        "routeDifferenceIds": route_diffs,
        "editDifferenceIds": edit_diffs,
        "reviewedRouteCounts": dict(Counter(row["route"] for row in baseline)),
        "liveRouteCounts": dict(Counter(row["route"] for row in live)),
        "modelsUsed": manifest["modelsUsed"],
        "responseModesUsed": manifest["responseModesUsed"],
        "note": "Agreement is between two artifacts for this supplied dataset, not hidden-ground-truth accuracy.",
    }
    destination = ROOT / "artifacts/live/comparison.json"
    destination.write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Compared {len(live)} reports: {len(agreement)} verdict/repair agreements, "
          f"{len(route_diffs)} route differences, {len(edit_diffs)} edit differences.")


if __name__ == "__main__":
    main()
