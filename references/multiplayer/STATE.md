# Multiplayer and persistence invariants

| Boundary | Required tests |
|---|---|
| Join/leave/rejoin | initialize once, detach subscriptions, restore allowed state |
| Respawn/round change | rebind character-dependent state, clear obsolete UI, no duplicate events |
| Concurrent purchase | reject insufficient funds, charge exactly once, avoid stale shared writes |
| Ownership/permissions | server-authoritative decision, deny cross-player operations |
| UI | personal widgets not leaked to other players; focus/touch/gamepad |
| Persistent schema | old save loads, new optional defaults, future-compatible versioned schema |
| Resource lifecycle | task cancellation, no orphaned device listeners or retained player refs |

Do not assume a general SQL server is available from Verse. Inspect current persistable `weak_map` restrictions and memory budgets using Epic sources, versioned knowledge and digest. Do not migrate live persistable classes automatically. Specify whether user-level vs character-level persistence is possible before implementing a garage. Use a single persistent writer per domain and maintain an idempotency boundary for purchases. Real load tests and multiplayer evidence remain separate from static review.
