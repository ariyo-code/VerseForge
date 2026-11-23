# VERSEFORGE / CONTROL CENTER (LOT 05)

**Only show a menu if the skill is invoked without a task.** The user must never navigate the menu to make an explicit request, such as “Crée un téléphone RP avec Verse UI”.

Display no more than the following seven simple choices, in the conversation's language:

> **VERSEFORGE — Que veux-tu faire ?**
>
> 1. **Créer un système** — téléphone, garage, inventaire
> 2. **Corriger un bug** — Verse et UEFN
> 3. **Créer une interface** — menus, HUD, téléphone RP
> 4. **Optimiser** — vitesse et stabilité
> 5. **Analyser un projet** — architecture et problèmes
> 6. **Aide Verse et UEFN** — API, devices et explications
> 7. **Paramètres** — installation, connexion et licence
>
> Choisis un numéro ou décris directement ta demande.

If a user selects an option, ask **only one appropriate short question** using `vf guide --choice N` as an optional aid. Once they provide details, immediately route into the matching workflow; do not re-show the menu. The host must preserve the user's existing context (attachments, constraints, selected style).

`vf guide --choice 1 --details "Garage RP avec écran FiveM, export ZIP" --can-create-files` produces a deterministic handoff, **not** Verse code or native UI.

When no scripted tool is available, follow these same rules conversationally. Native buttons/forms are optional only if the host actually supports them; this skill cannot force them into existence.

The image-to-UEFN reverse-engineering feature is **not implemented**; do not list it as a working option.
