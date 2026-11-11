import {
  Action,
  Case,
  Edit,
  getPayload,
  Question,
  ReviewRequest,
  Taxonomy,
  Workspace,
} from "./types";

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const count = (s: string, find: string) => (find ? s.split(find).length - 1 : 0);

export function mathErrors(value: string): number {
  const stack: string[] = [];
  let errors = 0;
  const tags = value.matchAll(/<(\/?)([a-zA-Z][\w-]*)(?:[^>"']|"[^"]*"|'[^']*')*>/g);
  for (const token of tags) {
    const tag = token[2].toLowerCase();
    if (token[0].endsWith("/>")) continue;
    if (!token[1] && (tag === "math" || stack.length)) stack.push(tag);
    else if (token[1] && stack.length) {
      if (stack[stack.length - 1] !== tag) errors++;
      else stack.pop();
    }
  }
  return errors + stack.length;
}

export function validatePatches(c: Case, patches: Edit[], taxonomy: Taxonomy): string[] {
  const errors: string[] = [];
  const rule = c.decision.repair ? taxonomy.repairs[c.decision.repair] : null;
  if (!Array.isArray(patches) || patches.length > 12) return ["Invalid patch list"];
  if (patches.length && (!rule || c.decision.verdict !== "defect"))
    return ["This finding cannot carry a content patch"];
  for (const p of patches) {
    if (
      !p ||
      !["question", "solution", "answer", "questionType"].includes(p.field) ||
      !rule?.fields.includes(p.field)
    ) {
      errors.push("Field is outside this repair's scope");
      continue;
    }
    const original =
      p.field === "questionType" ? c.question.questionType : getPayload(c.question)[p.field];
    if (same(p.find, p.replace)) errors.push("The patch makes no change");
    if (p.field === "answer" || p.field === "questionType") {
      if (!same(original, p.find)) errors.push("Source value is stale");
    } else if (
      typeof original !== "string" ||
      typeof p.find !== "string" ||
      typeof p.replace !== "string" ||
      !p.find ||
      count(original, p.find) !== 1
    ) {
      errors.push("Find text must match exactly once");
    } else {
      if (/<\s*(script|iframe|object|embed|svg)|\bon\w+\s*=|javascript:/i.test(p.replace))
        errors.push("Unsafe replacement markup");
      if (c.decision.repair === "answer_form" && !p.replace.includes(p.find))
        errors.push("Answer-form changes must be additive");
      if (
        c.decision.repair === "option_repair" &&
        (original.indexOf("(A)") < 0 || original.indexOf(p.find) < original.indexOf("(A)"))
      )
        errors.push("Option repairs must preserve the stem");
      if (c.decision.repair === "spelling") {
        const tokens = (s: string) => s.match(/<[^>]+>|\d+(?:\.\d+)?|[^\p{L}\p{N}_\s]/gu) || [];
        if (!same(tokens(p.find), tokens(p.replace)))
          errors.push("Spelling changes cannot alter math, values, or tags");
      }
      if (
        c.decision.repair !== "solution_missing" &&
        p.find.length > Math.max(160, original.length * 0.65)
      )
        errors.push("The proposed replacement is too broad");
      const replaced = original.replace(p.find, () => p.replace as string);
      if (mathErrors(replaced) > mathErrors(original))
        errors.push("The replacement damages MathML nesting");
    }
  }
  if (!errors.length) {
    try {
      const q = applyPatches(c.question, patches);
      const answer = getPayload(q).answer;
      if (q.questionType === "scq" && (typeof answer !== "string" || !/^[A-D]$/.test(answer)))
        errors.push("SCQ answer must be one option label");
      if (
        q.questionType === "mcq" &&
        patches.length &&
        (!Array.isArray(answer) ||
          !answer.length ||
          answer.some((a) => !/^[A-D]$/.test(a)) ||
          new Set(answer).size !== answer.length)
      )
        errors.push("MCQ answer must contain individual unique option labels");
      if (
        q.questionType === "integerQuestion" &&
        (typeof answer !== "string" || !/^-?\d+$/.test(answer))
      )
        errors.push("Integer answer must be an integer string");
      if (!["scq", "mcq", "integerQuestion"].includes(q.questionType))
        errors.push("Unknown question type");
    } catch {
      errors.push("Patch could not be applied atomically");
    }
  }
  return [...new Set(errors)];
}

export function applyPatches(question: Question, patches: Edit[]): Question {
  const q = structuredClone(question);
  const originalType = q.questionType;
  const body = getPayload(q);
  for (const p of patches) {
    if (p.field === "questionType") {
      if (!same(q.questionType, p.find) || typeof p.replace !== "string")
        throw new Error("Stale type");
      q.questionType = p.replace;
    } else if (p.field === "answer") {
      if (!same(body.answer, p.find)) throw new Error("Stale answer");
      body.answer = structuredClone(p.replace);
    } else {
      if (
        typeof p.find !== "string" ||
        typeof p.replace !== "string" ||
        count(body[p.field], p.find) !== 1
      )
        throw new Error("Ambiguous span");
      body[p.field] = body[p.field].replace(p.find, () => p.replace as string);
    }
  }
  if (q.questionType !== originalType) {
    q[q.questionType] = body;
    delete q[originalType];
  }
  return q;
}

export function transition(
  state: Workspace,
  request: ReviewRequest,
  c: Case,
  taxonomy: Taxonomy,
  at = new Date().toISOString(),
): Workspace {
  if (state.audit.some((a) => a.id === request.requestId)) return state;
  if (request.expectedVersion !== state.version || request.sourceHash !== c.sourceHash)
    throw new Error("This case changed. Refresh before reviewing.");
  if (!["approve", "edit", "reject"].includes(request.action))
    throw new Error("Unknown review action");
  if (
    typeof request.reason !== "string" ||
    request.reason.length > 800 ||
    ((request.action === "reject" || request.action === "edit") && !request.reason.trim())
  )
    throw new Error("Add a short reason for this action");
  if (state.reviews[c.id] && state.reviews[c.id].status !== "draft")
    throw new Error("This case has already been reviewed in this workspace");
  const errors = validatePatches(c, request.patches, taxonomy);
  if (errors.length) throw new Error(errors.join("; "));
  // Reviewer edits stay drafts until a separate approval.
  const after =
    request.action === "approve" && request.patches.length
      ? applyPatches(c.question, request.patches)
      : c.question;
  const manual = c.decision.verdict === "defect" && !request.patches.length;
  const status =
    request.action === "reject"
      ? "rejected"
      : request.action === "edit"
        ? "draft"
        : manual
          ? "needs_authoring"
          : "approved";
  return {
    version: state.version + 1,
    reviews: {
      ...state.reviews,
      [c.id]: { status, patches: request.patches, question: after, at },
    },
    audit: [
      {
        id: request.requestId,
        caseId: c.id,
        action: request.action as Action,
        actor: "Demo faculty",
        at,
        reason:
          request.reason.trim() ||
          (manual
            ? "Finding accepted; human-authored repair required"
            : "Reviewed evidence and proposal"),
        before: c.question,
        after,
        patches: request.patches,
        sourceHash: c.sourceHash,
      },
      ...state.audit,
    ],
  };
}
