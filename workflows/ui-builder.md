# Visual UI / UMG handoff and experimental Verse UI generation

For an explicit image reconstruction task, the **host vision model** must first produce an observation JSON with normalized widget bounds, evidence categories (`observed`, `inferred`, `user-specified`, `unknown`) and explicit navigation targets. It must not claim to recover original source code from pixels.

Commands:

```bash
python scripts/vf.py visual-inspect --image reference.png
python scripts/vf.py ui-render --spec examples/visual-two-screen.json --output /tmp/vf-umg-preview --emit-verse
```

Outputs: browser `preview.html` (positioned, original mock), `UMG_HANDOFF.json` (widget plan), `IMPLEMENTATION.md`, and optionally `Verse/vf_generated_ui_device.verse` plus `VERSE_UI_STATUS.json`.

The generated Verse source is **experimental**. It renders basic text and buttons and handles explicit screen navigation/close through a per-player canvas with cleanup. Unknown gameplay events are not silently wired. It has not been compiled in UEFN and does not create actual UMG `.uasset` assets. High-fidelity UMG needs an editor importer and authoring support; implement via authorized live UEFN MCP tools when available, and record evidence.

Do not use the HTML prototype as if it were an interactive Fortnite HUD. Compare a real Fortnite screenshot, controller focus and touch targets in UEFN before accepting.
