# BUILD / actual source workflow (LOT 02)

1. **X-Ray** `vf build-context --request ... --project ...`; inspect `files[].classes`, `files[].weak_maps`, `potential_economy_owners`, `warnings`. Read relevant source and git/URC status before proposing a change. Avoid duplicating canonical managers.
2. **API verification** use upstream `verse-ai claim` via `vf api-check` for signatures, parameters, returns and effects. Verify events/payloads when used. Local installed UEFN `*.digest.verse` takes version priority. When evidence is absent, `TODO(API VERIFY)` and design a safe alternative. Do not promote speculative API calls.
3. **Architect** output expected files, API claim ledger, state ownership, lifecycle, permissions, acceptance cases, editor device bindings and UMG/asset requirements. For a paid garage, integrate the project's existing wallet and protect idempotent charges; never replace with an unrelated new bank.
4. **Generate Verse** as the host coding agent, writing full usable classes (not just plans). Use `examples/benchmarks` for grounded patterns, NOT as a universal text template. Prefer minimal coherent changes; provide plain `*.verse` code.
5. **Preview** compose `verseforge-edits-v1` proposal JSON; `vf proposal --project ... --plan edits.json` validates SHA preconditions, class conflicts, paths, file sizes and structural heuristics. Inspect expected diff yourself. Apply only within explicit project scope using `--apply`, record `backup_batch` for rollback.
6. **Validate** `vf xray` + `vf static-review` and upstream `verse-ai lint` where present. Never claim that Python PASS means Verse compiled. On a real editor, discover MCP names/schemas, call current Verse compile tool and capture raw log. Do not invent exact tool names. Manually compile from UEFN menu when MCP absent.
7. **Repair** `vf repair-analyze --log exact.log`, select smallest root-cause fix and recompile. Record candidate hashes and stop after repeated errors (default 3) or unsafe scope change.
8. **Test** PIC behavior, multiplayer 2+ players, reconnect, late join, simultaneity, persistence and rollback. Separate skipped from passed. Confirm UI input gamepad/touch.
9. **Deliver** changed file list, API evidence, actual editor build result, regression evidence, limitations and rollback ID.

Stop immediately on destructive migration, missing exact API verification on critical path, uncertain player data loss or 3 failed identical repair attempts. Ask user permission for a published island data schema change.
