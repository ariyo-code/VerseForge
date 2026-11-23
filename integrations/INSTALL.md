# Installation (public skill)

Python 3.11+ recommended for helper scripts. No external files or code run on installation.

- Codex: copy directory `verseforge/` to `~/.agents/skills/verseforge` or project `.agents/skills/verseforge` (follow host's active discovery paths).
- Claude Code: copy to `~/.claude/skills/verseforge` or project `.claude/skills/verseforge`.
- Cursor: copy to project `.cursor/skills/verseforge` or user skill location where supported.

Run `python scripts/vf.py validate`, `python scripts/vf.py doctor --knowledge /absolute/path/to/Verse-AI-Knowledge`. Install `verse-ai-knowledge` separately from its own repository if needed (respect its license). Never bundle the upstream proprietary repository into this package.

For editor integration configure UEFN's own generated MCP client config (see `UEFN_MCP.md`). The optional private-service is not necessary for the public skill to work in offline advisory mode. Licensing rules cannot prevent a reader from copying public Markdown. Do not publish this package until license text and redistribution permissions are finalized.
