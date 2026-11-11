# Acadza Report → Fix

The original assignment remains in README.md. This document describes the implementation, not a replacement brief.

## Current behavior

- Python exports 44 report records and 39 grouped faculty cases from the supplied snapshot.
- `reviewed` mode uses the transparent assistant-reviewed catalog in `engine/reviewed.py`, bound to immutable input hashes. It is **not** an API run or a general-purpose solver.
- `live` mode uses the configured provider for two blind solves and report-aware adjudication. It does not consult reviewed decisions. Model agreement alone never authorizes a substantive automatic edit.
- A complete Groq candidate is retained in `artifacts/live/`. Its 44 verdict/repair pairs agree with the reviewed snapshot, but it withholds more supported edits; the reviewed snapshot remains the console default. The Run details view discloses this comparison.
- The console renders sanitized HTML and MathML, shows exact replacements and rendered previews, supports approve/edit/reject, and records before/after versions.
- With PostgreSQL, review state persists in a signed, isolated visitor workspace. Without it, the console clearly labels browser-local storage. No production Acadza data or student messaging service is connected.

## Install and run (Windows PowerShell)

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r engine/requirements.txt
npm.cmd ci
.venv/Scripts/python.exe -m engine.cli --mode reviewed
npm.cmd run dev
```

Open http://127.0.0.1:3000. Run commands from the repository root. Node 22 and Python 3.14 were available during implementation; exact JavaScript versions are recorded in package-lock.json.

## Configure live inference

Copy `.env.example` to `.env` and set `GROQ_API_KEY`. The default `GROQ_MODEL=openai/gpt-oss-120b` supports strict structured outputs. Groq is selected when its key is present; the previous Gemini adapter remains available if only `GEMINI_API_KEY` and `GEMINI_MODEL` are configured. Never paste a key into prompts, source, or issue reports.

```powershell
# Inspect available models; uses the configured provider key without displaying it.
.venv/Scripts/python.exe -m engine.list_models

# A one-question smoke run does not replace results.json.
.venv/Scripts/python.exe -m engine.cli --mode live --limit 1

# Prefer a candidate run while reviewing model outputs.
.venv/Scripts/python.exe -m engine.cli --mode live --candidate --batch-size 1 --max-api-calls 150 --min-request-interval 20

# Resume cached cases with explicit, repeatable Groq model switches.
.venv/Scripts/python.exe -m engine.cli --mode live --candidate --batch-size 1 --model-switch 15:qwen/qwen3.8-27b --model-switch 31:openai/gpt-oss-120b --max-api-calls 60 --min-request-interval 45

# Promote only after reviewing a complete candidate.
.venv/Scripts/python.exe -m engine.cli --promote-live
```

The recommended Groq run uses **117 successful requests**: one question at a time, each with a blind solve, an independent blind verification, and adjudication. An eight-question batch trial produced incorrect blind calculations for R005; the single-question smoke solved that case correctly. The optional batch path remains implemented and exact-ID-validated but is not the preferred quality path. Groq's documented free plan has request and token limits. The examples explicitly set a 150-attempt ceiling; the CLI defaults remain 30 attempts and 20 seconds for conservative trial runs. A stopped candidate can resume from cached successful calls. If multiple Groq models are used, each case and the manifest record its model. Blind inputs contain no stored keys, solutions, or student comments.

Cached responses consume no request budget. Groq rate errors use bounded retries when a short retry delay is supplied; daily token exhaustion stops the run. Transient server errors also have bounded retries within the same ceiling. Repeated strict-schema generation errors can use Groq JSON-object mode with the exact Pydantic schema appended to the prompt; the object must still pass Pydantic validation. A timeout can still consume provider quota. Responses are cached by model, generation settings, prompt, schema, and input in ignored `artifacts/private-runs/`. Refusals, truncation, invalid output, and exhausted API requests stop the run instead of fabricating decisions. Candidate runs save completed cases and an explicit interruption reason without replacing the main output. Cache files contain actual requests/responses and must be reviewed/redacted before sharing. Student identifiers are excluded from the adjudication payload. API keys are never written to run logs.

`GROQ_REASONING_EFFORT=low` reduces latency without removing the separate verification call. Generation-setting changes invalidate the corresponding cache key. A frozen baseline is retained in `artifacts/baseline/` for transparent comparison. The earlier Gemini attempt confirmed a 20-request/day free-tier quota and completed seven grouped cases before quota exhaustion. Partial actual output is retained in `artifacts/attempts/`. The completed Groq run, its model switches, response modes, and zero-call policy replay are recorded in `PROMPTS.md`, `artifacts/live/manifest.json`, and `docs/live-comparison.md`.

The product prompt files are versioned in `engine/prompts/`; their full wording is also recorded in PROMPTS.md. Exact per-call payloads are in private cache records, not falsely reconstructed after a run.

## Verification

```powershell
.venv/Scripts/python.exe -m pytest engine/tests -q
.venv/Scripts/python.exe -m engine.cli --validate-only
.venv/Scripts/python.exe scripts/compare_live.py
npm.cmd run test:web
npm.cmd run typecheck
npm.cmd run build
```

Coverage is not accuracy against hidden labels. Check `docs/verification-record.md` for actual results and outstanding verification.

## Deployment to Vercel

The live console is [acadza-report-fix-eight.vercel.app](https://acadza-report-fix-eight.vercel.app/). Project `acadza-report-fix` is connected to the public GitHub repository. Vercel uses Next.js, Node 24, Root Directory `apps/console`, and includes source files outside that directory for shared contracts and artifacts. The repository npm workspace build command is `npm run build`; Next.js uses its default output directory. The CLI was linked from the repository root.

`DATABASE_URL` and `SESSION_SECRET` are configured as Vercel secrets for Production and Preview. No Groq key was deployed: inference runs offline, while the console reads a precomputed reviewed snapshot. The public URL returned HTTP 200 without Vercel authentication; the real production PostgreSQL review flow was verified in an isolated workspace. Keep the deployment and database available for seven days from submission.

The application initializes `acadza_workspaces` on first database access. The database user needs permission to create this table. Its JSONB state is updated with an optimistic version comparison, keeping a review action and its audit event atomic. This is a scoped demo store, not production SSO or a privileged institutional faculty account.

## Contract and policy assumptions

- `repair` and `edit` are null when inapplicable. Internal multi-edit proposals are atomic; their singular evaluation `edit` is null instead of silently exporting only part of the proposal. They always require faculty review. This convention is explicit because README supplies no multi-edit schema.
- `auto_apply` is a proposed route, not a claim that this dry-run export has changed production data. Replies say a correction is ready. A console approval applies it only in the demo workspace.
- Confidence is an ordinal, uncalibrated evidence rating, not an empirical correctness probability. The manifest documents the mapping.
- Missing-option reconstruction without original wording is held for faculty. Single-correct MCQs are not automatically assumed to be type defects.
- `already_fixed` needs matching history and current content. `updatedAt` is not enough.
- Syllabus cases are review requests; the question remains live. The closed taxonomy has no separate 'pending syllabus check' verdict.
- Existing malformed HTML is preserved as source. Sanitization changes presentation only. New MathML nesting damage is rejected.
- The current generic-report convention checks academic correctness and records incidental, unreported text defects separately. No hidden ground-truth labels are available.

## Submission checklist

- [x] Public GitHub repository and committed results.json
- [x] Genuine complete live candidate and explicit reviewed/precomputed console disclosure
- [x] Public faculty console URL and persistent review storage verified
- [ ] Seven-day availability after submission
- [x] PROMPTS.md with exact prompts and genuine failures
- [x] PRODUCT.md, at most one page
- [ ] Three-minute recording (see docs/demo-script.md)
- [ ] Email with the three links and your own commitment/start-date/motivation answers

The recording and submission email remain the applicant's deliverables; their completion is not implied by this checklist.
