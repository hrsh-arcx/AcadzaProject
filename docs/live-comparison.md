# Reviewed snapshot and completed Groq candidate

The console and root `results.json` use the assistant-reviewed snapshot. The separate Groq candidate is in `artifacts/live/`. It completed all **44 reports / 39 grouped cases** and passed the result contract. A zero-call replay used all 117 cached model responses to apply the final deterministic policy; the manifest preserves the pre-replay hash. The final inference invocation made 23 API calls and reused 94 cached responses; earlier failed or interrupted attempts are recorded in `PROMPTS.md` and are not included in that invocation count.

| Measure | Reviewed snapshot | Groq candidate |
| --- | ---: | ---: |
| Report coverage | 44 | 44 |
| Auto apply proposals | 12 | 3 |
| Faculty review | 15 | 24 |
| No change | 17 | 17 |
| Singular evaluation edits | 18 | 11 |

All **44 verdict/repair pairs agree between these two artifacts**. They differ in nine routes and ten singular edits; see `artifacts/live/comparison.json` for exact report IDs and hashes. This is an internal comparison, **not** accuracy against hidden labels.

The reviewed snapshot remains the faculty demo default because it retains supported, precise edits that the live candidate left blank, including restoration proposals for missing stem values (R006–R008), the raw fraction markup (R014), and the requested numerical unit (R024). These edits still pass deterministic validation; missing-source and scoring decisions that need faculty judgement remain review cases. The live candidate is a genuine model-generated comparison with two recorded Groq model switches, strict JSON Schema responses, and one validated JSON-object fallback. No live proposal was applied to production content.
