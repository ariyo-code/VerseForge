# Validation ladder and evidence rules

| status | Minimum credible proof |
|---|---|
| draft | file/code exists; may include unresolved exact API claims |
| static-checked | identified static checks run and passed against this exact artifact; no unsupported claim |
| compiled | real installed UEFN Verse compile success tied to artifact hash and timestamp |
| verified | compiled + observed functional runtime acceptance tests with logs/session |
| multiplayer-verified | verified + observed >=2 players testing contention, disconnect/respawn and permissions |

Never promote from an inferred status. Record tool availability, command, UTC time, artifact/content hash and log path. Preserve failures and skipped tests in report. If provenance signature is valid but compile unobserved, compilation = `NOT TESTED`. Keep knowledge trust level separate from code validation.
