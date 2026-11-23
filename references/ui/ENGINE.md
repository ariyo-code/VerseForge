# UI ENGINEERING / design DNA

UI categories: UMG widget blueprint, Verse UI widget, hybrid UMG–Verse integration. Check real editor version and available binding APIs. Create per-player UI controller, one owner for widget lifecycle and a state→render model. Avoid full-tree rebuild for a numeric update. Maintain keyboard/mouse, gamepad focus, touch targets, safe areas, HUD conflicts and localization. UI workflow: screenshot analysis → component diagram → Design DNA → capabilities matrix → assets/license proof → create widgets/textures → bind events → editor/session tests. A generated icon PNG is NOT an imported asset or functioning widget.

Default project `assets/design-dna.example.json`: customizable type scale, spacing, tokens, interaction states. `assets/design-styles.json` offers FiveM/GTA/Roblox etc as **original style directions only** (do not copy protected UI). `assets/sources.json` gives links and per-source license review state. Asset attribution must follow each actual file's license, not the catalog entry.

Concrete `templates/ui-screens/garage.json` represents a screen as state, layout and permission-gated commands. `vf ui-plan` merges it with the selected art direction and project Design DNA. It does **not** produce Verse widgets or import UMG files automatically.


## 0.9.0-rc1 – Asset traceability gate

For portable ZIP export, every binary resource under `UI/` or `Assets/` must be listed in root `ASSET_MANIFEST.json`, schema `verseforge-asset-manifest-v1`. Each entry contains path, SHA-256, creator/origin, and an explicit recognized license. Third-party entries require HTTPS source and license URLs, plus attribution for MIT/ISC/CC-BY. See `scripts/verseforge_core/asset_license.py` for the exact contract. The manifest is a user declaration, **not legal proof**. Verify rights and Epic IP rules before publication. Never distribute unlicensed source art or fonts.
