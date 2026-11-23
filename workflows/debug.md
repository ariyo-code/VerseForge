# DEBUG / controlled repair loop (LOT 02)

- Obtain an **actual** compiler log/UEFN MCP response; preserve it verbatim, including editor version, file line and timestamps. `vf repair-analyze --log FILE` extracts errors into a structured report; it does not fix code itself or confirm the log came from UEFN.
- Use the upstream error memory (`verse-ai search`, read-only) and validate field-level signatures. Read source near the failure; diagnose root causes and propose the minimal edit without losing functionality.
- Save the proposed revised file in an `edits` JSON with old SHA; call `vf proposal` preview then `--apply` after reviewing. Compile again in actual UEFN if connected. Preserve resulting log.
- Track a JSON array of attempts `{ "candidate_sha256": "...", "compiler_log_sha256": "...", "outcome": "..." }`. `vf repair-next --history history.json --candidate-sha256 HASH --max-attempts 3` rejects repeats and excessive retries. Do not feed fabricated output into evidence promotion.
- If the edit worsens the result, use `vf rollback --project PROJECT --batch BATCH` (refuses overwriting work changed since application). Stop if same error persists 3 attempts, sources are insufficient or persistent schema risk emerges.
- Never modify Verse-AI-Knowledge error memory in place without separate permission. Report compiler status `NOT TESTED` when UEFN is unavailable.
