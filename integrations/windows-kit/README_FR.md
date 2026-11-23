# VerseForge LOT 03 — Kit de validation Windows UEFN

**UEFN n'a pas été exécuté lors de la création de ce kit.** Toutes les validations suivantes sont à réaliser sur un PC Windows équipé d'UEFN et de Fortnite. Travaillez sur une **copie** du projet ou une île de test.

## Préparer l'éditeur

1. Lancez UEFN avec le projet de test. Vérifiez la version affichée dans les informations de l'éditeur (ne la déduisez pas du dépôt de connaissances).
2. Dans UEFN : **Edit > Editor Preferences > Agentic Workflows > Model Context Protocol** ; démarrez le serveur avec **Start Server** et utilisez **Generate Client Config** pour votre agent. Suivez le chemin créé par UEFN (souvent dans `.../Fortnite/FortniteGame`), sans inventer de configuration.
3. Vérifiez que les toolsets adaptés sont activés selon la version de l'éditeur. **N'activez pas Execute Python** pour ce kit ; les outils Python non contrôlés sont hors périmètre.
4. Démarrez Codex / Claude Code / Cursor depuis le dossier pour lequel la configuration a été créée. Si le port 8000 est déjà utilisé, choisissez le port depuis UEFN et adaptez `-Endpoint`.
5. Ouvrez PowerShell dans le dossier `integrations/windows-kit` du skill. Utilisez `./Diagnose-UEFN.ps1 -Project 'C:\...\TestProject' -Endpoint 'http://127.0.0.1:8000/mcp' -Probe`.
6. Examinez le registre des outils MCP : `python ../../scripts/vf.py mcp-registry --endpoint http://127.0.0.1:8000/mcp` ; sélectionnez un véritable outil de compilation disponible et ses **paramètres découverts**.

## Installer les benchmarks dans la copie du projet

1. Choisissez un répertoire Verse existant et autorisé sous le répertoire contenant le `.uefnproject` de **test**.
2. Prévisualisez : `./Stage-Benchmarks.ps1 -ProjectRoot 'C:\...\TestProject' -TargetVerseDirectory 'C:\...\TestProject\Verse' -Benchmark A`
3. Ajoutez `-Apply` pour copier les fichiers. Aucun fichier existant n'est écrasé. `-Benchmark ALL` copie A/B/C, mais testez d'abord A seul.
4. Dans UEFN, ouvrez le projet, configurez les `@editable` dans le niveau et les boutons de popup conformément aux commentaires des fichiers. La préparation des devices est une étape indispensable.
5. Pour compiler manuellement : **Verse > Build Verse Code**. Si le MCP connecté expose réellement une opération de compilation, son nom et son schéma doivent être lus via `mcp-registry`. Préparez alors un `arguments.json` conforme à ce schéma puis exécutez, **uniquement sur le projet de test** :

   ```powershell
   python ../../scripts/vf.py compile --project 'C:\...\TestProject' --endpoint http://127.0.0.1:8000/mcp --tool 'NOM_DECOUVERT' --arguments .\arguments.json --files 'vf_interactive_notice_device.verse' --evidence-dir '.\proofs' --confirm-uefn-compile
   ```

6. En cas d'échec, archivez les diagnostics exacts, vérifiez la version des API et proposez une correction minimale avec empreinte SHA-256. Le moteur `repair-session` consomme des propositions **rédigées par un agent** et garde les sauvegardes. Il ne crée pas automatiquement des corrections sans fondement.

## Gameplay et multijoueur

- A : bouton configuré + HUD Message. Vérifiez le message pour le joueur concerné ; avec deux clients, vérifiez que l'autre ne reçoit rien.
- B : testez ouverture, fermeture, vue 1→2→1 et indépendance de deux joueurs.
- C : créez deux spawners configurés, configurez le popup 0=Claim, 1=Retrieve, 2=Store. Testez le cycle, l'occupation des places, la déconnexion et la persistance après redémarrage de session.
- Lancez une **Play-in-Client (PIC)** session UEFN, et non PIE. Notez nombre de clients, version UEFN, procédure suivie, résultat observé et preuves. Un lancement de session n'est pas une validation de comportement.
- Utilisez `Collect-Compiler-Log.ps1` sur un fichier journal existant et préalablement revu afin de constituer une copie locale expurgée.

## Critères et limites

Les statuts ne sont promus qu'après vérification indépendante : `draft` → `static-checked` → `compiled` → `verified` → `multiplayer-verified`. Les tests Python, mock MCP et captures manuelles non vérifiables ne suffisent pas.

Les procédures sont fondées sur : https://dev.epicgames.com/documentation/fortnite/uefn-mcp et https://dev.epicgames.com/documentation/fortnite/python-scripting-with-uefn-mcp. Les noms exacts des outils du serveur varient et ne sont **pas** présumés ici.
