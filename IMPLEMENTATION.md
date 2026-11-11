# Acadza Report → Fix

The original assignment remains in README.md. This document describes the implementation, not a replacement brief.

## Current behavior

- Python exports 44 report records and 39 grouped faculty cases from the supplied snapshot.
- `reviewed` mode uses the transparent assistant-reviewed catalog in `engine/reviewed.py`, bound to immutable input hashes. It is **not** an API run or a general-purpose solver.
- `live` mode uses Gemini for two blind solves and one adjudication per question. It does not consult reviewed decisions. Model agreement alone never authorizes a substantive automatic edit.
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

## Configure Gemini

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` and `GEMINI_MODEL` to a structured-output-capable model available in your account. Never paste the key into prompts, source, or issue reports.

```powershell
# Inspect available generateContent models; uses the key without displaying it.
.venv/Scripts/python.exe -m engine.list_models

# A one-question smoke run does not replace results.json.
.venv/Scripts/python.exe -m engine.cli --mode live --limit 1

# A complete run replaces the reviewed artifact only after complete validation.
.venv/Scripts/python.exe -m engine.cli --mode live

# Prefer a candidate run while reviewing model outputs.
.venv/Scripts/python.exe -m engine.cli --mode live --candidate --batch-size 8 --max-api-calls 20 --min-request-interval 20

# Promote only after reviewing a complete candidate.
.venv/Scripts/python.exe -m engine.cli --promote-live
```

A full uncached run now needs **15 successful requests**: five batches of up to eight grouped questions, each with a blind solve, a separate blind verification, and adjudication. Batch size 1 retains the original per-question mode (117 calls). The default ceiling is 20 attempted requests per invocation, with a minimum 20 seconds between request starts. Every batch must return all requested question IDs exactly once; no missing, duplicated, or invented IDs are accepted. Blind batches contain no stored keys, solutions, or student comments.

Cached responses consume no request budget. HTTP 429 stops immediately; transient server errors have bounded retries within the same ceiling. A timeout can still consume provider quota. Responses are cached by model, generation settings, prompt, schema, and input in ignored `artifacts/private-runs/`. Refusals, truncation, invalid output, and exhausted API requests stop the run instead of fabricating decisions. Candidate runs save completed cases and an explicit interruption reason without replacing the main output. Cache files contain actual requests/responses and must be reviewed/redacted before sharing. Student identifiers are excluded from the adjudication payload. API keys are never written to run logs.

`GEMINI_THINKING_LEVEL=low` is supported on the tested Gemini 3 Flash models and reduces latency without removing the separate verification call. Generation-setting changes invalidate the corresponding cache key. A frozen baseline is retained in `artifacts/baseline/` for transparent comparison. A real attempt confirmed a 20-request/day free-tier quota; the previous per-question run completed seven grouped cases before quota exhaustion. The batch implementation is tested structurally, but its full model run is pending available quota. Partial actual output is retained in `artifacts/attempts/`.

The product prompt files are versioned in `engine/prompts/`; their full wording is also recorded in PROMPTS.md. Exact per-call payloads are in private cache records, not falsely reconstructed after a run.

## Verification

```powershell
.venv/Scripts/python.exe -m pytest engine/tests -q
.venv/Scripts/python.exe -m engine.cli --validate-only
npm.cmd run test:web
npm.cmd run typecheck
npm.cmd run build
```

Coverage is not accuracy against hidden labels. Check `docs/verification-record.md` for actual results and outstanding verification.

## Deployment to Vercel

1. Push this project to a public GitHub repository. Check the staged diff and secret ignore rules first.
2. Import it into Vercel, choose **Next.js**, and set Root Directory to `apps/console`. Enable inclusion of files outside that directory so shared contracts remain available.
3. Use the repository npm lockfile/workspace install. Build command: `npm run build`; Next.js output directory: default. If using the Vercel CLI, run it from `apps/console` and confirm the project root.
4. Add `DATABASE_URL` (a pooled PostgreSQL connection string) and a random `SESSION_SECRET` of at least 32 characters to Vercel. The console does not need the Gemini key; inference is an offline job.
5. Redeploy, check the public URL in an unauthenticated browser, and verify approval persistence after refresh. Keep the project and database available for seven days.

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

- [ ] Public GitHub repository and committed results.json
- [ ] Genuine live Gemini run, or explicit reviewed/precomputed disclosure
- [ ] Public faculty console URL, persistent review storage verified, seven-day availability
- [ ] PROMPTS.md with exact prompts and genuine failures
- [ ] PRODUCT.md, at most one page
- [ ] Three-minute recording (see docs/demo-script.md)
- [ ] Email with the three links and your own commitment/start-date/motivation answers

No public deployment, external API outcome, database verification, or recording is implied by this checklist.
