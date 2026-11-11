from engine.models import BatchProposals, BatchSolves
from engine.content import payload
from engine.provider import RequestTooLargeError


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
    # Adjudication carries full records and both blind solves. Three cases keep
    # the request below the observed Groq request-size ceiling for this dataset.
    def adjudicate(chunk):
        chunk_ids = [q["_id"] for q in chunk]
        adjudication = {"taxonomy": taxonomy, "cases": [{"question": q,
            "reports": [{k: r[k] for k in ("reportId", "reportedAt", "source", "comment")} for r in groups[q["_id"]]],
            "blind_solves": [first[q["_id"]], second[q["_id"]]]} for q in chunk]}
        try:
            return index_batch(provider.generate("adjudicate-batch-v2.txt", adjudication, BatchProposals).model_dump()["items"], chunk_ids)
        except RequestTooLargeError:
            if len(chunk) == 1:
                raise
            middle = len(chunk) // 2
            return {**adjudicate(chunk[:middle]), **adjudicate(chunk[middle:])}

    proposals = {}
    for start in range(0, len(questions), 3):
        proposals.update(adjudicate(questions[start:start + 3]))
    return {qid: (proposals[qid], [first[qid], second[qid]]) for qid in ids}
