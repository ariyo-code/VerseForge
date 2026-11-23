# Task routing / decision table

| Intent | Mode | Read next |
|---|---|---|
| invoke VerseForge without a specific request | CONTROL CENTER | control-center.md |
| plain chatbot output (code/ZIP) | CHAT MODE | chat-mode.md |
| inspect unknown project | DISCOVERY | discovery.md |
| system specification | DESIGN | design.md |
| build or integrate feature | BUILD | build.md |
| real compiler/runtime failure | DEBUG | debug.md |
| Verse hot path or heavy UI | OPTIMIZE | optimize.md |
| screenshot, widget, HUD | UI | ui-design.md |
| explicit reconstruction from a user image | UI (visual reference) | visual-reference.md |
| modify structure preserving behavior | REFACTOR | refactor.md |
| review security/quality | AUDIT | audit.md |
| precise API, version or signature | API_VERIFY | api-verify.md |
| acceptance/delivery | DELIVERY | delivery.md |

A request may need multiple modes, e.g. BUILD → UI → DEBUG → DELIVERY. Use only necessary references, not every file. Priority is user's explicit mode, project requirements, then topic classification; if no Fortnite/UEFN/Verse context do not activate this skill. Never treat a successful generic text search as signature-level evidence.
