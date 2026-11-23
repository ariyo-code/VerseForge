# Installer VerseForge — Guide rapide

1. Décompresser `verseforge-public.zip`. Le dossier racine doit s'appeler `verseforge` et contenir `SKILL.md`.
2. Le placer dans le dossier Agent Skills de votre environnement :
   - **Codex** : `.agents/skills/verseforge` dans le projet, ou `~/.agents/skills/verseforge`.
   - **Claude Code** : `.claude/skills/verseforge` dans le projet, ou `~/.claude/skills/verseforge`.
   - **Cursor** : `.cursor/skills/verseforge` dans le projet.
3. Vérifier le fonctionnement des outils locaux :

   ```powershell
   python scripts/vf.py validate
   python scripts/vf.py doctor --knowledge C:\\chemin\\Verse-AI-Knowledge
   python scripts/vf.py plan --request "Garage RP persistant avec UI FiveM"
   python scripts/vf.py ui-plan --style "FiveM Premium" --screen garage
   ```

4. Installer séparément `Verse-AI-Knowledge` si désiré, en respectant sa licence propriétaire. Le paquet VerseForge ne comprend pas sa copie.
5. Sur Windows avec UEFN, activer le serveur MCP intégré via **Editor Preferences → Agentic Workflows → Model Context Protocol**, puis utiliser **Generate Client Config** pour l'agent choisi. Ne pas inventer la configuration si l'éditeur n'est pas installé.
6. Vérifier que l'agent voit réellement les tools MCP puis demander : « Utilise VerseForge pour analyser mes fichiers Verse, vérifier les API et construire mon garage RP. »

La connexion à l'éditeur, la compilation et les tests de gameplay ne sont pas inclus dans l'archive. Le service de licences expérimental est livré **séparément** dans `verseforge-private-dev.zip` et ne doit pas être exposé publiquement.
