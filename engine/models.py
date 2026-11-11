from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Edit(StrictModel):
    field: Literal["question", "solution", "answer", "questionType"]
    find: str | list[str]
    replace: str | list[str]


class Result(StrictModel):
    reportId: str
    questionId: str
    verdict: Literal["defect", "no_error", "display_issue", "app_issue", "language_mode", "already_fixed", "not_actionable"]
    repair: str | None
    edit: Edit | None
    route: Literal["auto_apply", "faculty_review", "no_change"]
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(min_length=1, max_length=1800)
    student_reply: str = Field(min_length=1, max_length=700)


class Solve(StrictModel):
    answer: str | list[str] | None
    derivation: str
    assumptions: list[str]
    sufficient_data: bool


class Proposal(StrictModel):
    verdict: Result.model_fields["verdict"].annotation
    repair: str | None
    patches: list[Edit]
    evidence: str
    student_reply: str
    unresolved: bool


class QuestionSolve(Solve):
    questionId: str


class BatchSolves(StrictModel):
    items: list[QuestionSolve]


class QuestionProposal(Proposal):
    questionId: str


class BatchProposals(StrictModel):
    items: list[QuestionProposal]

