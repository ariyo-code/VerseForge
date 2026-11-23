# VerseForge 1.0.0-rc4 — Engineering & delivery pipeline (NOT production-certified)

This development snapshot extends 0.9.0-rc1 with **four new functional engines**, but must not be mistaken for a validated end-to-end Fortnite code generator:

1. **Engineering Engine** validates a 48-module dependency graph, rejects duplicate mutable state owners, emits a build plan and optional *placeholder* Verse devices. The active coding model still authors real gameplay behavior.
2. **UI Engine** converts an explicit host/user observation map into a standalone browser preview, UMG editor handoff and optionally a basic uncompiled Verse UI canvas for text and navigation/close. Native `.uasset` creation and automatic extraction of UI logic from a screenshot do not exist here.
3. **Asset Engine** discovers 15 catalogued sources without granting rights; imports explicitly reviewed local artwork, transforms image dimensions when requested, validates hashes and attribution; no automatic third-party asset downloads or claimed independent legal review.
4. **Distribution and Owner Console** creates/verifies deterministic public skill ZIP files, installs with backups, supports rollback, and provides an OIDC-gated private web console for licenses and owner audit logs. Full IdP, payment and hardened hosting remain external tasks; a separate offline detached Ed25519 release-signing command is now available, with key trust managed out-of-band.

Try locally (inside the public `verseforge/` directory):

```bash
python scripts/vf.py architect --spec examples/city-rp-architecture.json
python scripts/vf.py ui-render --spec examples/visual-two-screen.json --output /tmp/vf-ui --emit-verse
python scripts/vf.py release-build --version 1.0.0-rc4 --output /tmp/verseforge.zip
python scripts/vf.py release-verify --file /tmp/verseforge.zip
python scripts/vf.py validate
```

See `workflows/engineering-orchestrator.md`, `workflows/ui-builder.md`, `workflows/asset-pipeline.md`, `workflows/release.md` and `ci/README.md`.

**UEFN compilation, Fortnite gameplay, multiplayer, native agent activation and production OIDC deployment: NOT TESTED.**

---

# VerseForge 0.9.0-rc1 — Engineering release candidate

Agent Skills extension for evidence-based Fortnite UEFN / Verse engineering. It retains the LOT 01 `SKILL.md`, 10 workflows, 17 recipes, UI style catalog, and optional private provenance/license service, while adding real project inspection, diff-aware write/rollback, claim inspection, offline repair guards, and four Verse source files across three benchmarks.

**LOT 03 additions:** Stateful MCP Streamable HTTP client; opt-in discovered tool registry; environment diagnosis; observational Verse compile result contract with SHA-256 evidence; bounded agent-authored repair orchestrator; guarded MCP editor writes; Windows PIC validation kit and 3-benchmark gameplay/multiplayer matrix. No real UEFN editor was connected in this Linux build environment. See `integrations/windows-kit/README_FR.md`.

**Honest boundary:** The coding agent itself authors code; these Python utilities validate and apply the agent's proposals but do **not** independently synthesize arbitrary Verse from natural language. No UEFN editor/Verse compiler or LLM host was available in the build environment. 43.10 is Epic's documented current public release on 2026-11-22; the upstream knowledge repository's V25 snapshot remains 42.20.

## 0.9.0-rc1 — Host Chat, Visual Reference, Quality, Licensing Foundations

**Release candidate, NOT production-certified.** This update preserves every LOT 01–05 function and adds:

- `vf quality-review --source STAGING [--contract requirements.json]`: static source hygiene, SHA-256 and required text checks. Literal evidence never certifies behavior.
- `vf deliver --source STAGING --output PACKAGE.zip [--contract requirements.json] [--strict]`: stage an agent's previously written Verse, replace untrusted validation claims, export and independently verify a ZIP. The source directory is not changed.
- `vf visual-inspect --image screenshot.png`: local dimensions, SHA-256 and approximate sampled colors only (Pillow optional); no automatic recognition of buttons/code.
- `vf visual-plan --spec observations.json [--image screenshot.png]`: validate host-vision component positions, evidence labels, behavior uncertainty and output a UMG/Verse UI plan. Does NOT create native UMG assets or compile Verse.
- **Asset provenance gate**: `UI/` and `Assets/` resources require an `ASSET_MANIFEST.json` with every asset hash, declared creator/license and URL/attribution where relevant. This does not independently verify legal rights.
- **Optional OIDC resource service** in private sources: verifies an externally issued OAuth JWT with pinned issuer/audience and a nominated, revocable VerseForge license bound to the same subject. Includes owner-only REST administration endpoints. The private service is **not a fully compliant MCP server**, there is no deployed Identity Provider or production admin web panel, and no commercial distribution authorization.
- An offline fresh-source ChatGPT coding trial with full artifact hash verification; **neither true host-skill activation nor a UEFN build was run**.

Documentation: `workflows/quality-and-delivery.md`, `workflows/visual-reference.md`, `integrations/CHATGPT_FR.md`, `examples/acceptance.example.json`, `examples/visual-observations.example.json`.

Example commands:

```bash
python scripts/vf.py validate
python scripts/vf.py menu
python scripts/vf.py quality-review --source STAGING --contract examples/acceptance.example.json
python scripts/vf.py deliver --source STAGING --output feature.zip --strict
python scripts/vf.py package-verify --file feature.zip
python scripts/vf.py visual-inspect --image your-reference.png
python scripts/vf.py visual-plan --spec examples/visual-observations.example.json
```

## LOT 05: Guided Control Center, task routing and ZIP verification

- Direct Verse/UEFN requests bypass the menu. Invoking the skill without a task shows **seven** beginner-friendly choices. `vf guide --choice N` asks **one** short follow-up; `--details` routes to the correct workflow without returning to the menu. The chatbot itself keeps conversational context.
- `vf chat-route` now handles French accents and direct tasks with embedded UI requirements: e.g. « Crée un garage RP avec interface » routes to BUILD, while « Crée une interface HUD » routes to UI. The CLI is not a model or real host tool detector.
- `vf package-verify --file OUT.zip` independently checks the archive file list and SHA-256 integrity, rejects duplicate/unsafe names and unsupported validation claims, and does not extract its contents. SHA-256 integrity is **not** an Ed25519 signature.
- See `integrations/LOT05_HOST_VALIDATION_FR.md`: true activation tests on ChatGPT/Codex/Claude/Cursor remain **NOT TESTED** here. Windows UEFN compilation and gameplay also remain **NOT TESTED**.

```bash
python scripts/vf.py menu
python scripts/vf.py guide --choice 1
python scripts/vf.py guide --choice 1 --details "Garage RP avec interface, en ZIP" --can-create-files
python scripts/vf.py package --source STAGING --output OUT.zip
python scripts/vf.py package-verify --file OUT.zip
```

## LOT 04: Chat Mode and Control Center

- `python scripts/vf.py menu` shows seven beginner-friendly options, not a native universal UI.
- `python scripts/vf.py chat-route --request "Crée un garage ZIP" --can-create-files` routes to code/ZIP/project based on **declared host capabilities**.
- `python scripts/vf.py package --source STAGING_DIR --output OUTPUT.zip` safely packages existing Verse sources from `Verse/` and approved resources. The agent must create the code itself; this script cannot generate Verse.
- No UEFN access/compile is implied by a successful ZIP export. See `workflows/chat-mode.md` and `integrations/CHAT_MODE_FR.md`.

## Quick start

```bash
python scripts/vf.py validate
python scripts/vf.py doctor --knowledge /path/to/Verse-AI-Knowledge
python scripts/vf.py build-context --request "Add a garage to my existing RP economy" --project /path/to/your/island --output /tmp/context.json
python scripts/vf.py api-check --repo /path/to/Verse-AI-Knowledge --fields signature,parameters,return_type,effects button_device
python scripts/vf.py xray --project /path/to/your/island
python scripts/vf.py proposal --project /path/to/your/island --plan /path/to/agent-authored-edits.json
python scripts/vf.py proposal --project /path/to/your/island --plan /path/to/agent-authored-edits.json --apply
# Undo by backup_batch returned by --apply:
python scripts/vf.py rollback --project /path/to/your/island --batch ID
```

`proposal` accepts a JSON object like:

```json
{"schema":"verseforge-edits-v1","purpose":"Add button event handler","changes":[{"path":"Verse/vf_demo.verse","old_sha256":null,"new_content":"vf_demo := class(creative_device):\n    Enabled:logic = true\n"}]}
```

For an existing file, `old_sha256` MUST equal the file's actual SHA-256; null is valid only for a new file. This avoids clobbering concurrent/human edits. A structural checker will reject conflicting class declarations. Full generated code must come from your real coding agent, not the placeholder content above.

## Commands

- `validate`, `doctor`, `scan`, `plan`, `ui-plan`, `knowledge`, `provenance-verify` — retained from LOT 01.
- `xray`, `build-context` — read-only project structure, module/state-owner analysis and agent context.
- `api-check` — call upstream `verse-ai claim` field-by-field, never inventing `ALLOW`.
- `proposal` / `rollback` — preview/apply complete `.verse` files with hash preconditions and backups.
- `static-review` — local heuristics **not compiler proof**.
- `mcp-config` / `mcp-probe` — inspect actual client configuration / enumerate loopback MCP schemas without invoking editor tools.
- `mcp-call` — opt-in `tools/call` on a discovered live loopback MCP tool, validates actual input JSON Schema (`jsonschema` optional dependency), requires `--confirmed` on every call and additionally `--allow-mutation` for operation names that appear mutating. No automated claim of UEFN compilation.
- `repair-analyze` / `repair-next` — parse exact logs and block repeated changes.
- `promote` — check shape of evidence status transition; does not authenticate external logs.

See `examples/benchmarks/README.md`, `integrations/UEFN_MCP.md` and `references/validation/LOT02_EVIDENCE.md`. Private licensing/signing prototype is a **separate development-only archive**. No secrets in public source.

## LOT 03 commands (live editor only, never with mocks)

```bash
python scripts/vf.py environment --project /path/to/test-island --endpoint http://127.0.0.1:8000/mcp --probe
python scripts/vf.py mcp-registry --endpoint http://127.0.0.1:8000/mcp
# Following command requires actual discovered tool name and schema-valid input:
python scripts/vf.py compile --project /path/to/test-island --endpoint http://127.0.0.1:8000/mcp --tool ACTUAL_COMPILE_TOOL --arguments arguments.json --files YourDevice.verse --evidence-dir /path/to/proofs --confirm-uefn-compile
```

Use `mcp-sync-edit` for a single file edited through the MCP server with SHA-256 preconditions. Use `repair-session` with an existing failed compile report and agent-authored candidate edit plans for bounded repair attempts. Every operation requires explicit operator approval; see `SKILL.md` for the full contract. Do not assume any tool is called `ACTUAL_COMPILE_TOOL`—this is an example placeholder.

The CLI may return a compilation `SUCCESS` **reported by an arbitrary MCP tool**; this alone cannot authenticate the editor's identity or authorize status promotion. Verify the run in the actual UEFN editor and correlate its build output with the evidence file.

## Release 1.0.0-rc3: installation integrity and deterministic device generation

```bash
python scripts/vf.py recipe-button-hud --spec examples/button-hud-recipe.json --output /tmp/my-verse-device
python scripts/vf.py deliver --source /tmp/my-verse-device --output /tmp/my-verse-device.zip
python scripts/vf.py release-build --skill-root . --version 1.0.0-rc3 --output /tmp/verseforge-public.zip
python scripts/vf.py release-verify --file /tmp/verseforge-public.zip
```

The install/rollback pipeline checks all installed content hashes before replacement. Release SHA-256 is *not* authenticity; verify signed releases with a publisher key obtained through a trusted channel. No real UEFN compile, native host activation, or gameplay test has been run.

## 1.0.0-rc4: unified project delivery

```bash
python scripts/vf.py bundle-project \
  --spec examples/city-rp-architecture.json \
  --source /path/to/agent-authored-staging \
  --output /path/to/new-delivery-folder \
  --uefn-version 43.10 \
  --ui-spec examples/visual-two-screen.json
```

The required Verse module names must match the engineering architecture, and source files must exist **before** the bundle begins. Optional licensed asset import takes `--asset-spec` and `--asset-root` together. Bundle checks are offline and cannot certify compilation, UI fidelity, game physics, multiplayer, or a connected UEFN editor.
