# LOT 02 Evidence model

The Python scripts are a controlled **filesystem handoff**, not a Verse compiler or a language model. Agent authors code; `vf xray`, `vf build-context`, `vf proposal` and `vf rollback` inspect, gate, write and restore. An autonomous coding agent must read exact `verse-ai` field evidence and local UEFN digests before creating unsupported API claims.

* `draft`: code authored without complete proof.
* `static-checked`: evidence record of local static checks. Lightweight `vf static-review` only checks limited heuristics; its PASS is not sufficient alone to assert correct Verse syntax, type checking or API compatibility.
* `compiled`: actual editor result and raw compile log SHA-256.
* `verified`: actual PIC runtime test and raw evidence.
* `multiplayer-verified`: at least two real client test records; not simulated players.

`vf promote` enforces forward step transitions and demands evidence; it verifies record shape, **not authenticity of an editable JSON document**. Only trust evidence directly captured by a connected host tool or human-supplied log with its origin checked.
