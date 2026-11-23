# Asset engine — local import, transformation and licensing

1. Gather resources from user-provided or explicitly licensed sources. Do not scrape sites, download third-party graphics without permission, or reproduce a brand's paid assets.
2. Prepare `verseforge-asset-import-v1` JSON with each local source path, target `UI/` or `Assets/`, license, origin, creator or URL, and `rights_reviewed: true` only after actual user/legal confirmation.
3. Execute:

```bash
python scripts/vf.py assets-import --spec asset-import.json --root SOURCE_DIR --output NEW_STAGING_DIR
```

4. The tool checks file type signatures, rejects symlinks/traversal/oversized files, optionally normalizes images to PNG, calculates SHA-256, writes `ASSET_MANIFEST.json` and human-readable credits. `asset_license` verifies consistent claims and hashes when packaging.
5. Import textures/icons/audio into UEFN through the editor and configure UMG references; no automatic `.uasset` is created by this offline utility.

**No network retrieval, automatic proof of copyright rights, font distribution or native UEFN import is implemented.** Rely on source licenses plus real editor steps; UEFN import is `NOT TESTED` until performed.

### Curated asset discovery (v1.0.0-rc2)

Search the reference catalog without downloading or assuming rights:

```bash
python scripts/vf.py asset-sources --query lucide --category icon
python scripts/vf.py asset-sources --reviewed-only
```

A catalog match NEVER authorizes import or redistribution; obtain, vet and declare each individual file before `assets-import`.
