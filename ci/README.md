# VerseForge CI templates

These YAML files are templates, not activated GitHub Actions while stored here.
Copy the appropriate workflow into `.github/workflows/` in the chosen repository.

- `public-ci.yml` expects a repository with `SKILL.md` at its root.
- `owner-ci.yml` expects `verseforge/` and `private-service/` at its root. The owner repository must remain private.

CI verifies Python behavior and package reproducibility. A green GitHub check **does not mean Verse compilation, Fortnite runtime or multiplayer passed**. Connect a Windows self-hosted UEFN runner only with real editor evidence and explicit project permissions.

For signed releases, run `vf release-sign` on a separate trusted owner machine after CI and distribute the signature alongside the release. The CI does **not** automatically acquire production signing keys.
