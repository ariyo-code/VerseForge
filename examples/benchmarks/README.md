# VerseForge LOT 02 — reproducible Verse engineering benchmarks

The four `.verse` files in three scenarios are **actual original Verse source**, not JSON placeholders. They were created from a design reviewed against current Epic documentation. **No Verse compilation, gameplay, device placement or UMG import was performed** in this environment. `vf static-review` is Python pattern review only; it does not parse or compile Verse.

## A — interactive device

* `A-interactive-device/vf_interactive_notice_device.verse`
* Add one `vf_interactive_notice_device`, one Button and one HUD Message device to the island.
* Assign both editable device references to the objects placed in the level.
* Compile with Verse > Build Verse Code, launch a PIC session, interact with the button using player 1 and player 2 separately.
* Expect each player to see a message containing their own agent reference; no global broadcast. End session and check no further callbacks are retained.
* Status: `draft`; static heuristic review `PASS`; compile/runtime/multiplayer `NOT TESTED`.

## B — interactive Verse UI

* `B-verse-ui/vf_two_view_ui_device.verse`
* Add one `vf_two_view_ui_device` and a Button device; bind `OpenButton` in the Details panel.
* Enter a PIC session, press the Button, navigate between Home/Details using `Switch view`, close with `Close`.
* With two players, ensure independent displays, views, and cleanup on leaving. Run gamepad/touch tests.
* Uses Verse UI (canvas, button_loud/button_regular), **not a UMG asset**.
* Status: `draft`; static heuristic review `PASS`; compile/runtime/multiplayer `NOT TESTED`.

## C — modular RP starter garage

* `C-rp-garage/vf_garage_profile.verse`, `C-rp-garage/vf_starter_garage_device.verse`
* Create `vf_starter_garage_device`, a Button, a Popup Dialog and a HUD Message device; add **at least two** `vehicle_spawner_sports_car_device` spawners, assigned as `CarSpawners`.
* In the Popup Dialog editor UI configure exactly three buttons: index 0 **Claim**, 1 **Retrieve**, 2 **Store**. Assign references. Verify popups display and respond to each agent independently.
* Test: claim once and repeat, leave/rejoin (entitlement should remain), retrieve (actual spawner call), store (actual destroy call), two players retrieve concurrently with two spawners, a third player receives a full-garage message, player leaves while slot allocated, fresh round begins. Verify editor spawner settings so no unintended auto-spawns.
* **Important:** this scenario implements persistent **starter entitlement**, not purchases or bank debits; it is NOT a paid garage. It reserves spawner bays but cannot enforce physical anti-theft or driver locks, and does not persist a spawned physical vehicle's transform, damage or customization. Those require separate verified game systems and API/tool evidence. Integrate with existing economy/profile only after Project X-Ray; avoid adding a conflicting `weak_map` on an existing published island.
* Status: `draft`; static heuristic review `PASS`; compile/runtime/multiplayer/persistence-in-published-island `NOT TESTED`.

## Evidence and test protocol

Read `api-evidence.json` for the exact Epic pages inspected and unresolved evidence. The source ledger represents **documentation evidence**, not a local verified SDK digest or proof that these examples compile. Run `python scripts/vf.py xray --project /path/to/island` and `python scripts/vf.py static-review --file ...` to produce local evidence; then use UEFN MCP discovered `Verse` toolset or the UEFN menu to build. Attach the compiler's raw output. Every failing line must be fixed using the smallest diff and a follow-up compile, not by deleting game features.

To compare an agent with/without VerseForge, use three fresh runs per prompt, same model and identical editor/session/knowledge access, and record token usage, time, API uncertainty, compile failures, regression count and game-test results. No LLM comparative run is claimed in this release.
