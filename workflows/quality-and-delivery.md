# VERSEFORGE / QUALITY & DELIVERY

1. Host agent creates full `.verse` sources in a staging directory with clear file names, no private files or third-party code lacking authorization. Never claim that the CLI is an independent language model.
2. Run `vf quality-review --source STAGING --contract acceptance.json` (contract optional). Text matches show *evidence of a literal*, not behavior. Any `TODO(API VERIFY)` must remain a blocker for affected functionality.
3. Run `vf deliver --source STAGING --output RESULT.zip --contract acceptance.json`. This validates the code heuristically, replaces any untrusted VALIDATION.md with a generated report, packages the sources, and verifies the ZIP integrity. `--strict` blocks if static checks need review. Source staging is not mutated.
4. External assets require `ASSET_MANIFEST.json` with per-file SHA-256, ownership or third-party license claims, URLs and attribution. A manifest can be dishonest: an actual license/rights review is still required before redistribution.
5. Signature: ZIP SHA-256 manifest is not a cryptographic attestation. Use the separate authorized private Ed25519 signer when available; never bundle the private key. Do not interpret the signing receipt as proof of generation, UEFN compilation or gameplay correctness.
6. Actual UEFN compilation, PIC testing and multiplayer isolation need the real editor and actual evidence. No `compiled` or `verified` claims without it. `vf quality-review` never promotes status.
7. Report: created files, static warnings, exact API claims, requested behavior vs delivered functionality, installation steps, residual limitations, real build status and tests.
