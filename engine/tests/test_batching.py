import pytest
from engine.batching import index_batch, generate_batch
from engine.models import BatchSolves, BatchProposals
from engine.cli import load_data


def test_batch_requires_every_requested_id_exactly_once():
    assert index_batch([{"questionId": "a", "answer": "A"}, {"questionId": "b", "answer": "B"}], ["b", "a"]) == {"a": {"answer": "A"}, "b": {"answer": "B"}}
    for items in [[{"questionId": "a"}], [{"questionId": "a"}, {"questionId": "a"}], [{"questionId": "a"}, {"questionId": "invented"}]]:
        with pytest.raises(ValueError, match="exactly once"):
            index_batch(items, ["a", "b"])


def test_blind_batch_inputs_exclude_keys_solutions_and_reports():
    questions, reports, taxonomy = load_data()
    q = questions[0]
    groups = {q["_id"]: [r for r in reports if r["questionId"] == q["_id"]]}
    seen = []
    class Fake:
        def generate(self, prompt, data, model):
            seen.append((prompt, data))
            if model == BatchSolves:
                return BatchSolves(items=[{"questionId": q["_id"], "answer": "C", "derivation": "test", "assumptions": [], "sufficient_data": True}])
            return BatchProposals(items=[{"questionId": q["_id"], "verdict": "display_issue", "repair": None, "patches": [], "evidence": "test", "student_reply": "test", "unresolved": False}])
    result = generate_batch(Fake(), [q], groups, taxonomy)
    assert result[q["_id"]][0]["verdict"] == "display_issue"
    assert seen[0][1] == seen[1][1]
    for _, data in seen[:2]:
        assert set(data["cases"][0]) == {"questionId", "questionType", "question", "quesImages"}
    assert "studentId" not in str(seen[2][1])
