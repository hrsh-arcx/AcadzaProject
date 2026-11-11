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

- Added a request ceiling and pacing. The quota-error policy stops immediately on HTTP 429. Cached responses use no inference request budget.
- After these changes, 24 Python tests passed, including four request-budget/cache/quota/pacing tests. Later changes require a final rerun before submission.
- The first larger live attempt reused the three smoke-test cache entries, then timed out on its first new request. The run recorded one completed case and `complete: false`; the root results.json remained intact. A timed-out request may still consume provider quota; no zero-cost claim is made.
- Checked the official Gemini thinking documentation and configured the supported low thinking level to reduce latency. This changes the generation configuration and therefore the cache key; old medium/default responses are preserved separately.
- Public GitHub destination supplied by the user: https://github.com/hrsh-arcx/AcadzaProject. Initial read showed no remote refs.
- Vercel CLI is installed via npm exec but initially reported logged out. No deployment is claimed.

## Browser verification limitation

The in-app browser access host was unavailable. Windows Computer Use then stopped because it could not reliably determine the browser URL. No screenshot, responsive-layout, clicking, or browser-local persistence verification is claimed. Unit tests cover transitions and sanitization, but do not substitute for visual/browser QA.

## External dependencies still requiring verification

- Complete live run and semantic review of the actual results.
- Real PostgreSQL persistence/concurrency behavior with a configured database.
- Public production deployment and unauthenticated access.
- Seven-day availability (requires leaving deployment and storage active).
- Actual three-minute screen recording and viewing permissions.

Update this file with actual results, failures, commands, and limits as they occur.

## Latest verified outcomes

- Python suite: **27 passed**, including batch ID coverage and blind-input isolation tests.
- Console suite: **13 passed**, including the actual route handlers' unconfigured-storage, cross-origin, and request-size checks.
- Production build passed after bundling local fonts and fixing local root .env loading.
- Real PostgreSQL HTTP verification passed at http://127.0.0.1:3100: approval, a subsequent GET with identical persisted state, draft editing, rejection, audit atomicity, one winner/one HTTP 409 for conflicting writes, and an idempotent retry. The script created four audit events in a new isolated test workspace and printed no credentials or cookies.
- The integration checks exposed two real defects beyond the unit suite: cached Next environment loading initially ignored root .env, and the initial origin check rejected legitimate requests when Next's internal URL used localhost. Both were corrected before the successful HTTP check. Cross-origin writes still fail the route-handler test.
- Gemini 3.8's larger run encountered timeouts. A Gemini 3.5 verifier completed; its subsequent per-question run completed **10 reports / 7 grouped cases** before an HTTP 429.
- Sanitized provider error details identified `GenerateRequestsPerDayPerProjectPerModel-FreeTier` with quota value **20**. A later Gemini 3.6 batch trial also returned 429 immediately. No complete external-model run is claimed, and no more inference calls should be made until quota is available.
- Batch v2 reduces a full run to 15 successful generation requests while retaining separate blind stages. This is an engineering estimate from five batches, not a claimed completed inference run.
