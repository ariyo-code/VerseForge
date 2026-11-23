# Product and distribution — public skill only

```bash
python scripts/vf.py release-build --skill-root . --version 1.0.0-rc4 --output ../verseforge-public-release.zip
python scripts/vf.py release-verify --file ../verseforge-public-release.zip
python scripts/vf.py release-install --file ../verseforge-public-release.zip --target /path/to/skills/verseforge
# On a future update (explicit; keeps a versioned backup):
python scripts/vf.py release-install --file NEW.zip --target /path/to/skills/verseforge --upgrade
python scripts/vf.py release-rollback --target /path/to/skills/verseforge --backup /path/to/skills/verseforge.backup-OLDVER
```

The ZIP is deterministic, manifest-hashed, bounded and restricted to public skill material. The installer checks hashes before any write, avoids symlinks, and renames an existing installation into a versioned backup before upgrading. It does not automatically configure host application permissions or connect UEFN.

**SHA-256 verification is not Ed25519 provenance.** A malicious publisher could recompute an unsigned manifest. Trust your distribution source; use the existing separate signed provenance system for source receipts and implement signed release metadata before commercial rollout.

CI templates are under `ci/`. They are not installed GitHub Actions until copied into `.github/workflows`.

## Optional detached Ed25519 release signature

**Keep the signing key only on a secure owner machine**, never in public archives or Git commits.

```bash
# Secure owner machine: reuse an Ed25519 issuer key OR generate a dedicated release key offline.
python scripts/vf.py release-sign --file ../verseforge-public-release.zip --private-key /secure/release-private.pem --output ../verseforge-release-signature.json
# Recipient must obtain the publisher public key via an authenticated out-of-band channel:
python scripts/vf.py release-signature-verify --file ../verseforge-public-release.zip --signature ../verseforge-release-signature.json --public-key /trusted/release-public.pem
```

A successful verification proves the ZIP was signed by the trusted key. It **does not** certify generated Verse, a valid licence, quality, or the editor version. Never publish the private PEM. Production key rotation and trust distribution still require operational work.
