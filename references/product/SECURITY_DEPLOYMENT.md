# Commercial release threat model and deployment gates

- Source Markdown remains readable to anyone who receives the public skill. Licensing cannot retroactively hide distributed plaintext.
- Keep the private issuer key, SQLite/DB, OIDC verification configuration and customer records on the private server. Never zip or commit secrets.
- Owner panel uses an existing authenticated OIDC resource-server service; it is not an identity provider, OAuth consent screen, secure login redirect flow, payments system or fully deployed commercial site.
- Owner panel keeps provided tokens only in page memory and sends them in Authorization headers; HTTPS, secure workstation, browser security and trusted IdP remain prerequisites.
- `owner()` checks nominated license and access token subject, role and `license:admin` on every write/read. No admin in offline development mode.
- Persisted admin actions have an SQLite audit event with owner subject; production audit must additionally address retention, remote immutable storage and monitoring.
- Do not publish without TLS reverse proxy, rate limiting, key rotation/KMS, backups, disaster recovery, IdP account lifecycle and professional security review.
- The ZIP release manifest is hash integrity, not a publisher signature. Review artifact signing and key management before external distribution.

## RC3: installed-release integrity checks

`release-install --upgrade` checks the installed file tree against its release manifest before changing it. `release-rollback` checks both the installed release and the candidate backup. Any local modifications or hidden/symlinked files block the operation. Local SHA-256 verification is not publisher authentication; use the detached signature against a trusted publisher key. Review and back up local changes manually before upgrading.

## RC4: atomic project deliveries

`bundle-project` writes into a temporary staging tree and publishes a new directory only when asset review gates, source checks and ZIP integrity succeed. It does not overwrite an existing delivery and does not authenticate the declared asset license; review of third-party rights remains mandatory. UI output is an HTML preview and editor handoff; native UMG assets are never asserted.
