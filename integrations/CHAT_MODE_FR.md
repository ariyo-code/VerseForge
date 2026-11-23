# VerseForge Chat Mode — guide utilisateur (LOT 05)

VerseForge fonctionne comme **instructions pour l'IA hôte**. Ce package ne contient pas son propre modèle de langage ni une interface de chat indépendante.

## Mode débutant

Invoquer `VerseForge` sans demande précise affiche sept options simples. Choisir `1` lance « Créer un système » et une seule question ciblée ; décrire directement « Crée un téléphone RP avec les contacts » lance immédiatement le travail, sans menu.

## Sorties

- **Code dans la conversation :** l'agent fournit les fichiers `.verse` complets et les consignes d'intégration. Aucune création de fichier n'est revendiquée.
- **ZIP :** si l'agent hôte peut créer des fichiers, il écrit les sources et lance `vf package`; `vf package-verify` contrôle le contenu et les empreintes. Le manifeste n'est pas une signature Ed25519 et ne certifie ni compilation ni gameplay.
- **Projet :** si l'agent est autorisé à écrire dans un workspace, il utilise les sauvegardes et le système de proposition/rollback. UEFN est facultatif mais indispensable à la compilation réelle.

## Installation des skills

Chaque chatbot dispose de ses propres mécanismes. Installer VerseForge via l'importation Agent Skills ou un adaptateur **que l'hôte reconnaît réellement**. Coller un `SKILL.md` dans un chatbot qui ne prend pas en charge ce format ne déclenche pas une installation automatique. Ne jamais promettre qu'une commande `/verseforge` est enregistrée sur un produit qui ne la propose pas.

Le menu peut être textuel ; les boutons natifs sont une possibilité propre à l'interface hôte, pas une fonction garantie du package.

## Commandes locales (Python 3.11+)

```bash
python scripts/vf.py validate
python scripts/vf.py menu
python scripts/vf.py guide --choice 1
python scripts/vf.py guide --choice 1 --details "Garage RP avec menu, en ZIP" --can-create-files
python scripts/vf.py package --source /CHEMIN/STAGING --output /CHEMIN/GARAGE.zip
python scripts/vf.py package-verify --file /CHEMIN/GARAGE.zip
```

Le code est écrit par l'IA hôte, **pas par** `vf guide` ou `vf package`. Les images et ressources tierces ne peuvent être redistribuées que si leur licence le permet.
