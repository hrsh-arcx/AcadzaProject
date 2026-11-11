# Verification record

All observations below concern the supplied snapshot and implementation. No hidden Acadza answer labels are available.

## Completed before this continuation

- Read README.md and the complete three supplied JSON files.
- Source inventory: 43 questions, 44 reports, 39 reported question IDs, no unresolved references or duplicated IDs. All source hashes are retained in engine/source-lock.json.
- Reviewed-mode export: all 44 reports present exactly once; case grouping yields 39 cases.
- Python suite: 20 passed after the initial validator failure was fixed.
- Console unit suite: 8 passed after the initial MathML editor failure was fixed.
- Production Next.js build completed successfully.
- One genuine Gemini 3.8 Flash smoke run completed with three generation calls. Both blind solves for R005 returned 1. The output was held for faculty review and did not replace the reviewed baseline.

## Continuation on November 11, 2026

- Added a request ceiling and pacing. Gemini daily quota errors stop immediately; Groq minute-limit retries are bounded and daily-limit errors stop. Cached responses use no inference request budget.
- After these changes, 24 Python tests passed, including four request-budget/cache/quota/pacing tests. Later changes require a final rerun before submission.
- The first larger live attempt reused the three smoke-test cache entries, then timed out on its first new request. The run recorded one completed case and `complete: false`; the root results.json remained intact. A timed-out request may still consume provider quota; no zero-cost claim is made.
- Checked the official Gemini thinking documentation and configured the supported low thinking level to reduce latency. This changes the generation configuration and therefore the cache key; old medium/default responses are preserved separately.
- Public GitHub destination supplied by the user: https://github.com/hrsh-arcx/AcadzaProject. Initial read showed no remote refs.
- Vercel CLI is installed via npm exec but initially reported logged out. No deployment is claimed.

## Browser verification limitation

The in-app browser access host was unavailable. Windows Computer Use then stopped because it could not reliably determine the browser URL. No screenshot, responsive-layout, clicking, or browser-local persistence verification is claimed. Unit tests cover transitions and sanitization, but do not substitute for visual/browser QA.

## External dependencies still requiring verification

- Public production deployment and unauthenticated access.
- Seven-day availability (requires leaving deployment and storage active).
- Actual three-minute screen recording and viewing permissions.

Update this file with actual results, failures, commands, and limits as they occur.

## Latest verified outcomes

- Python suite: **46 passed**, including batch ID coverage, size fallback, blind-input isolation, Groq request/limit behavior, key consistency, MCQ serialization, and atomic type-migration guards.
- Console suite: **13 passed**, including the actual route handlers' unconfigured-storage, cross-origin, and request-size checks.
- The final production Next.js build and TypeScript check passed after the dashboard's responsive text, per-case model labels, blind answers, and completed-run comparison card were added. HTTP GET on port 3100 returned 200 and the report queue. The connected browser host remained unavailable; no visual screenshot claim is made.
- Real PostgreSQL HTTP verification passed at http://127.0.0.1:3100: approval, a subsequent GET with identical persisted state, draft editing, rejection, audit atomicity, one winner/one HTTP 409 for conflicting writes, and an idempotent retry. The script created four audit events in a new isolated test workspace and printed no credentials or cookies.
- The integration checks exposed two real defects beyond the unit suite: cached Next environment loading initially ignored root .env, and the initial origin check rejected legitimate requests when Next's internal URL used localhost. Both were corrected before the successful HTTP check. Cross-origin writes still fail the route-handler test.
- Gemini 3.8's larger run encountered timeouts. A Gemini 3.5 verifier completed; its subsequent per-question run completed **10 reports / 7 grouped cases** before an HTTP 429.
- Sanitized provider error details identified `GenerateRequestsPerDayPerProjectPerModel-FreeTier` with quota value **20**. A later Gemini 3.6 batch trial also returned 429 immediately. That project quota is exhausted; no further Gemini calls have been made.
- The user replaced the local key with Groq. A real model listing showed `openai/gpt-oss-120b`; the first request needed an explicit user agent to pass Cloudflare. A one-case Groq batch smoke completed three actual generation calls for R005, with both blind answers `1`.
- An eight-question Groq batch produced wrong blind calculations for R005 (`1.5`, `5`) and an adjudication that misclassified R038. Its first 20 report results are preserved in `artifacts/attempts/groq-batch8-20-reports/`; later adjudication requests encountered HTTP 413. The batching code now splits oversized chunks, but the preferred quality run uses one question per batch.
- The one-question Groq run exposed a false R004 adjudication claim: both blind solves returned option D, but the model said D matched the stored key A. A deterministic guard now routes this contradiction to faculty without creating an unsupported key patch. A later HTTP 400 interrupted the run at case 12; a subsequent identical request succeeded.
- **Completed live candidate:** 44 reports / 39 grouped cases, complete manifest, result hash checked, and `validate_export` passed. The final inference invocation used 23 API calls and 94 cache hits; the zero-call final policy replay used 117 cached successful responses. The full sequence also includes earlier failed/interrupted attempts documented in `PROMPTS.md`. The candidate records GPT-OSS 120B and Qwen 3.8 27B per case, two model switches, strict JSON Schema responses, and one validated JSON-object fallback.
- `scripts/compare_live.py` validated both artifacts and wrote the exact comparison: **44/44 verdict/repair pairs agree**, nine routes and ten singular edits differ. This is agreement with the assistant-reviewed baseline, not hidden-label accuracy. The reviewed snapshot remains the console default because it retains more supported surgical edits (18 singular edits versus 11 live). See `docs/live-comparison.md`.
- A fresh real PostgreSQL HTTP check after the dashboard changes passed approval, persistence, draft edit, rejection, atomic audit, concurrent conflict, and idempotent retry in an isolated workspace. No student message was sent.
