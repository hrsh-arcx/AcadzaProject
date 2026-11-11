import type { Edit as ContractEdit, Result } from "../generated/contracts";
export type Verdict = Result["verdict"];
export type Edit = ContractEdit;
export type Field = Edit["field"];
export type Question = {
  _id: string;
  qid: string | null;
  questionType: string;
  subject: string;
  chapter: string;
  updatedAt: string;
  errorHistory: { type: string; actor: string; at: string; note: string }[];
  [key: string]: unknown;
};
export type Payload = {
  question: string;
  solution: string;
  answer: string | string[];
  quesImages: string[];
  solutionImages: string[];
};
export type Report = {
  reportId: string;
  questionId: string;
  studentId: string;
  source: string;
  reportedAt: string;
  comment: string;
};
export type Case = {
  id: string;
  model?: string | null;
  title: string;
  question: Question;
  reports: Report[];
  sourceHash: string;
  decision: {
    verdict: Verdict;
    repair: string | null;
    route: "auto_apply" | "faculty_review" | "no_change";
    confidence: number;
    evidence: string;
  };
  patches: Edit[];
  checks: { id: string; passed: boolean; evidence: string; value: number }[];
  blindSolves: {
    answer: string | string[] | null;
    derivation: string;
    assumptions: string[];
    sufficient_data: boolean;
  }[];
  validation: { passed: boolean; errors: string[]; scope: string[] };
  replies: Record<string, string>;
  priority: number;
  urgencyReason: string;
  oldestReport: string;
};
export type Taxonomy = {
  verdicts: Record<string, string>;
  repairs: Record<string, { fields: string[]; auto: boolean; label: string }>;
};
export type Review = {
  status: "approved" | "rejected" | "draft" | "needs_authoring";
  patches: Edit[];
  question: Question;
  at: string;
};
export type Audit = {
  id: string;
  caseId: string;
  action: Action;
  actor: string;
  at: string;
  reason: string;
  before: Question;
  after: Question;
  patches: Edit[];
  sourceHash: string;
};
export type Workspace = { version: number; reviews: Record<string, Review>; audit: Audit[] };
export type Action = "approve" | "edit" | "reject";
export type ReviewRequest = {
  caseId: string;
  sourceHash: string;
  expectedVersion: number;
  action: Action;
  reason: string;
  patches: Edit[];
  requestId: string;
};
export const emptyWorkspace = (): Workspace => ({ version: 0, reviews: {}, audit: [] });
export const getPayload = (q: Question) => q[q.questionType] as Payload;
