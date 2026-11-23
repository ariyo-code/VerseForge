# OPTIMIZE

Locate actual hot path and capture a repeatable baseline (Verse Insights / MCP where present). Check polling, event duplication, subscriptions, per-frame loops, UI update frequency, per-player arrays, string allocations, persistence writes, task cancellation, device count and network contention. Implement one change at a time; measure under equivalent conditions. Without profiling state 'hypothesized improvement, not measured' and preserve correctness over speed. Review related multiplayer race cases after optimization.
