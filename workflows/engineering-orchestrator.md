# Engineering orchestrator — project-scale RP and Verse

## Contract

An LLM/coding host writes the *behavior*. The engineering engine validates a declarative architecture, dependency DAG, exclusive ownership of named state, permission names, state scope and API claims. `architect` does not independently implement a complete requested game system.

1. Model each gameplay service as a module (`player`, `economy`, `inventory`, `vehicle`, `property`, `organization`, `job`, `moderation`, `ui`, `integration`, `custom`). Define exactly one owner for each mutable state namespace.
2. Use `python scripts/vf.py architect --spec examples/city-rp-architecture.json --output PLAN.json` to check dependencies, order, state writers and unverified API fields.
3. Optional *safe scaffold only*: add `--scaffold-dir NEW_EMPTY_DIR`. The output Verse devices are placeholders: they are not a banking, inventory, vehicle, staff or gameplay implementation and must never be delivered as such.
4. Inspect an existing project using `vf xray`; reconcile duplicated class names and weak_map owners before creating replacement code.
5. Check the local knowledge snapshot with `vf knowledge-audit --repo VERSE_AI_KNOWLEDGE --uefn-version 43.10` and resolve *each* API signature/effect claim using `vf api-check`. Unknown or mismatched snapshots are blockers for unchecked calls.
6. Agent authors full `.verse` code for each implemented vertical slice, creates acceptance contract and stages only approved changes. API-free scaffolds do not satisfy real functional requirements.
7. `vf quality-review`, actual compiler (when connected), session tests and multiplayer evidence are separate gates. Capture source SHA-256 and rollout/rollback details.

## Multisystem invariants

- Economy is the sole authority for money state and transactions; item/vehicle services request money changes through its service contract.
- Never expose direct mutation APIs without server-authoritative role checks.
- Avoid duplicate balances, weak_map records, double purchases and duplicated item grants. Use logical transaction IDs and idempotency where applicable.
- Data persisted through `weak_map(player, t)` must respect Epic compatibility and size constraints; no assumed global cross-server database.
- A static generated architecture and editor compilation status are unrelated evidence levels.
