import pytest
from engine.batching import index_batch, generate_batch
from engine.models import BatchSolves, BatchProposals
from engine.cli import load_data
from engine.provider import RequestTooLargeError


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


def test_large_blind_batch_splits_adjudication_without_losing_cases():
    questions, reports, taxonomy = load_data()
    selected_ids = list(dict.fromkeys(r["questionId"] for r in reports))[:8]
    selected = [next(q for q in questions if q["_id"] == qid) for qid in selected_ids]
    groups = {qid: [r for r in reports if r["questionId"] == qid] for qid in selected_ids}
    seen = []

    class Fake:
        def generate(self, prompt, data, model):
            seen.append((prompt, data))
            ids = ([item["questionId"] for item in data["cases"]] if model == BatchSolves
                else [item["question"]["_id"] for item in data["cases"]])
            if model == BatchSolves:
                return BatchSolves(items=[{"questionId": qid, "answer": "A", "derivation": "test",
                    "assumptions": [], "sufficient_data": True} for qid in ids])
            return BatchProposals(items=[{"questionId": qid, "verdict": "no_error", "repair": None,
                "patches": [], "evidence": "test", "student_reply": "test", "unresolved": False} for qid in ids])

    result = generate_batch(Fake(), selected, groups, taxonomy)
    assert set(result) == set(selected_ids)
    assert [prompt for prompt, _ in seen] == ["solve-batch-v2.txt", "verify-batch-v2.txt"] + ["adjudicate-batch-v2.txt"] * 3
    assert [len(data["cases"]) for _, data in seen] == [8, 8, 3, 3, 2]


def test_rejected_adjudication_recursively_splits_only_that_chunk():
    questions, reports, taxonomy = load_data()
    selected_ids = list(dict.fromkeys(r["questionId"] for r in reports))[:3]
    selected = [next(q for q in questions if q["_id"] == qid) for qid in selected_ids]
    groups = {qid: [r for r in reports if r["questionId"] == qid] for qid in selected_ids}
    sizes = []

    class Fake:
        def generate(self, _prompt, data, model):
            ids = ([item["questionId"] for item in data["cases"]] if model == BatchSolves
                else [item["question"]["_id"] for item in data["cases"]])
            if model == BatchSolves:
                return BatchSolves(items=[{"questionId": qid, "answer": "A", "derivation": "test",
                    "assumptions": [], "sufficient_data": True} for qid in ids])
            sizes.append(len(ids))
            if len(ids) > 1:
                raise RequestTooLargeError("test")
            return BatchProposals(items=[{"questionId": ids[0], "verdict": "no_error", "repair": None,
                "patches": [], "evidence": "test", "student_reply": "test", "unresolved": False}])

    assert set(generate_batch(Fake(), selected, groups, taxonomy)) == set(selected_ids)
    assert sizes == [3, 1, 2, 1, 1]
