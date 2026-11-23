# DESIGN

1. State business rules and acceptance conditions, including multi-session behavior and interface devices.
2. Identify single state owners and boundaries (player profile / economy / garage / UI controller / device adapters).
3. Draw dependency direction: `UI → application services → validated state/persistence`, and separate UEFN hardware/device entry points.
4. Enumerate exactly needed Verse API claims. Resolve every field with evidence or `TODO(API VERIFY)`; prefer installed digest for current editor.
5. Specify failure handling, atomicity/invariant for purchases, cancellation/disconnect, schema evolution, runtime load and clean-up.
6. Choose smallest reversible implementation slices and tests per slice. Include a rollback plan for writes or persistence migration.

Output architecture, interfaces, acceptance matrix and unresolved risks; not compiled code claims.
