from engine.models import BatchProposals, BatchSolves
from engine.content import payload


def index_batch(items, expected):
    """Reject missing, repeated, or invented question IDs before using a batch."""
    ids = [item["questionId"] for item in items]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("Batch response must contain every requested question exactly once")
    return {item["questionId"]: {k: v for k, v in item.items() if k != "questionId"} for item in items}


def generate_batch(provider, questions, groups, taxonomy):
    ids = [q["_id"] for q in questions]
    blind = {"cases": [{"questionId": q["_id"], "questionType": q["questionType"],
        "question": payload(q)["question"], "quesImages": payload(q)["quesImages"]} for q in questions]}
    first = index_batch(provider.generate("solve-batch-v2.txt", blind, BatchSolves).model_dump()["items"], ids)
    second = index_batch(provider.generate("verify-batch-v2.txt", blind, BatchSolves).model_dump()["items"], ids)
    adjudication = {"taxonomy": taxonomy, "cases": [{"question": q,
        "reports": [{k: r[k] for k in ("reportId", "reportedAt", "source", "comment")} for r in groups[q["_id"]]],
        "blind_solves": [first[q["_id"]], second[q["_id"]]]} for q in questions]}
    proposals = index_batch(provider.generate("adjudicate-batch-v2.txt", adjudication, BatchProposals).model_dump()["items"], ids)
    return {qid: (proposals[qid], [first[qid], second[qid]]) for qid in ids}
