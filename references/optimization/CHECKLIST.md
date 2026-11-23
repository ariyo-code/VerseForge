# Performance intelligence

Evidence priority: editor profiler/Verse Insights → instrumented runtime counters → static risk review. Capture before/after same player count, scene, hardware, run length and metrics. Examine excessive loops, polling intervals, repeated `GetPlayspace`-style lookups, duplicated subscriptions, per-player UI redraws, expensive `for` searches, N² scans, task cancellation, join/leave memory leaks, save-churn, reactive event storms and overgrown arrays. Never report numeric speedup from code inspection alone. If no profiler, label findings **predicted**, NOT measured.
