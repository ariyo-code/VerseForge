# VerseForge dans ChatGPT — guide français

## Installer, si la fonction Skills est disponible

Consulte la page d'aide officielle : https://help.openai.com/en/articles/20001066-skills-in-chatgpt . Dans les comptes éligibles, ouvrir **Plugins → Skills → Create → Upload from your computer**, puis choisir l'archive contenant le dossier `verseforge/` et son `SKILL.md`. L'installation n'est ni garantie ni vérifiée pour ce compte ou cette interface ; certaines offres ou surfaces ne proposent pas les Skills personnels. Un scan de sécurité peut bloquer certains fichiers ou demander une vérification supplémentaire.

Si l'interface ne propose pas l'importation des Skills, tu peux joindre le ZIP de VerseForge à une conversation disposant des outils nécessaires et demander à ChatGPT d'en suivre `SKILL.md` et les références pertinentes dans les limites de l'environnement. **Joindre un ZIP n'active pas nécessairement un Skill natif**, et les scripts Python ne deviennent pas exécutables dans tous les chatbots.

## Prompt simple d'utilisation

> Utilise le skill VerseForge joint pour ma demande Fortnite UEFN / Verse. Si je n'ai pas encore décrit mon objectif, affiche le menu en 7 choix. Sinon, passe directement au workflow adapté. Vérifie les API utilisées, écris de vrais fichiers `.verse`, fournis le code dans la conversation ou un ZIP si la création de fichiers est disponible. Ne revendique ni compilation UEFN ni test gameplay sans résultat réel.

## Modes

- **Code dans le chat** : donne chaque fichier intégralement, avec son nom, les références éditables à configurer, l'installation et le niveau de vérification.
- **ZIP** : l'agent produit les fichiers Verse, ajoute l'installation, passe `quality-review`, exporte avec `deliver` et vérifie avec `package-verify` lorsque ces scripts sont exécutables. Le ZIP n'est pas un projet `.uefnproject` importé, et les assets UMG natifs ne sont pas créés automatiquement.
- **Projet connecté** : uniquement si l'agent a réellement accès aux fichiers UEFN autorisés, avec preview/diff/rollback. La compilation exige un véritable UEFN et ses outils disponibles.
- **Image** : une image montrant une UI peut servir de référence visuelle. Il faut demander explicitement la reconstruction. Les pixels ne révèlent pas le code source, la persistance ou le comportement caché.

## Vérifier les résultats

Un rapport disant « tests Python réussis » ne prouve pas qu'un Verse compile. Vérifie les réglages des devices éditables, compile dans UEFN, teste en Fortnite et en multijoueur lorsque nécessaire. Pour les ressources tierces, vérifie les licences à l'échelle de chaque asset.

**Statut du candidat 0.9.0-rc1** : tests unitaires et d'intégration locale seulement ; installation native ChatGPT, compilation UEFN, PIC, multijoueur, OAuth réel et publication commerciale restent à vérifier.
