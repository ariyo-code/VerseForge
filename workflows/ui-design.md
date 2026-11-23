# UI / SCREENSHOT-TO-UI

1. Inspect image reference and existing UMG/Verse UI widgets. Extract layout regions, component tree, interaction states and input modes; do not assume image implies runnable UI.
2. Choose style from `assets/design-styles.json` or project Design DNA. Reuse user-authorized assets only.
3. Choose **actual** UMG, Verse UI or hybrid capability for every element based on local editor/API evidence. Flag unsupported features.
4. Produce component/state architecture and focus navigation across gamepad, keyboard/mouse and touch; ensure text scaling and safe areas.
5. Verify source/license of every icon via `assets/sources.json`; source unknown → do not import/redistribute.
6. Produce textures in correct format where tools exist; import and bind in editor only when tools exist; run game session to validate input and cleanup.
7. Report separately: mockup, asset-prepared, editor-imported, interactive, runtime-tested, multiplayer-tested.
