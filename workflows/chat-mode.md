# VERSEFORGE / CHAT MODE (LOT 05)

## A. Choose the fastest honest path

1. If the user states a concrete Verse/UEFN request, **skip the menu**. If not, show the seven choices in `control-center.md`.
2. If the user chooses a numbered item, ask one task-specific question only when essential; then continue.
3. Determine actual available host tools/permissions. The Python `chat-route` takes *declared* capabilities; it cannot discover permissions or activate a skill on another chatbot.
4. Honor explicit delivery preference: **chat code**, **ZIP**, or **edit project**. If impossible, state why and deliver the nearest useful fallback.
5. Research necessary Verse API signatures with installed digests, knowledge MCP or official Epic docs. Missing exact evidence => `TODO(API VERIFY)`. Do not invent compiler proof.

## B. Output contracts

**Code in chat**: provide complete `.verse` files, each with a relative path, plus device setup, required resources, assumptions, and verification state. Never imply generated text has been compiled.

**ZIP**: the host agent must actually create the Verse sources first, in a fresh staging area. Optional `UI/`, `Assets/`, `docs/` and `INSTALL.md` must contain only user-authorized work. Call `vf package --source STAGING --output ARCHIVE.zip`, then `vf package-verify --file ARCHIVE.zip`. The file hashes are not a digital signature and tests are `NOT TESTED` until independently run.

**Edit the project**: require a real, authorized project workspace; inspect, preview, apply and preserve rollback. UEFN real compiler/gameplay status is always `NOT TESTED` until a connected editor provides adequate evidence.

**Help/settings**: respond with actual documentation, configuration and diagnostics. Do not generate code/ZIP just because they are available. A local signed license prototype is not a deployed OAuth service.

## C. Clarity and low friction

- Respond in the user's language. Use simple French choice labels; keep technical terminology in the actual code and diagnostics.
- Avoid long questionnaires. Ask a short targeted question only if the missing information affects behavior or data safety; infer reversible cosmetic defaults and disclose them.
- Never ask for host/tool information already visible in the current session.
- For an uploaded image, analyze it as a reference; visual RE remains a research idea, not a validated reconstruction module.
- Final response: output files or link when actually created, installation steps, API uncertainty, compiler/gameplay/multiplayer statuses. For small tasks, be brief.

## D. Portable Control Center CLI examples

```sh
python scripts/vf.py menu
python scripts/vf.py guide --choice 1
python scripts/vf.py guide --choice 1 --details "Garage RP avec export ZIP" --can-create-files
python scripts/vf.py chat-route --request "Crée un inventaire UEFN" --can-create-files
python scripts/vf.py package --source STAGING --output OUT.zip
python scripts/vf.py package-verify --file OUT.zip
```

These commands do not host a chatbot, use a remote model, edit UEFN automatically, or guarantee native clickable controls.
