# VerseForge 0.5.0 — Validation sur les véritables chatbots

Les scénarios ci-dessous constituent une **procédure à exécuter** dans chaque agent hôte. Leur publication dans ce fichier ne constitue PAS un test d'activation sur Codex, Claude Code, Cursor ou ChatGPT.

| ID | Message utilisateur | Résultat attendu | Statut sur les hôtes |
|---|---|---|---|
| V01 | Invocation explicite sans tâche | Menu à sept choix, aucun code généré | NOT TESTED |
| V02 | « 1 » après le menu | Une question utile, sans répéter le menu | NOT TESTED |
| V03 | « Crée un garage RP avec UI » | BUILD direct ; pas de panel imposé | NOT TESTED |
| V04 | « Corrige cette erreur Verse » + source | DEBUG, lecture du vrai diagnostic | NOT TESTED |
| V05 | « Fais-moi un ZIP d'un système Verse » | ZIP réel si outils disponibles ; sinon fichiers en chat | NOT TESTED |
| V06 | « Analyse ce projet » | Projet lu seulement si accessible et autorisé | NOT TESTED |
| V07 | Demande sans rapport avec UEFN/Verse | Skill non invoqué automatiquement | NOT TESTED |
| V08 | Demande de compilation sans UEFN | Statut `NOT TESTED`, pas de succès inventé | NOT TESTED |

### Exécution

1. Installer le skill dans un vrai hôte compatible, selon sa propre procédure officielle.
2. Exécuter V01–V08 dans des conversations séparées (et V01→V02 dans la même session).
3. Noter : version de l'hôte, capture ou transcript, outils visibles, résultat, anomalies et lien vers la preuve.
4. Vérifier les sorties Verse avec les fichiers et l'éditeur UEFN lorsque disponibles ; sinon laisser `NOT TESTED`.

Le code Python peut tester le **routage déterministe**, le menu textuel et le ZIP local. Il ne peut pas prouver que l'hôte sélectionne réellement un skill en production.
