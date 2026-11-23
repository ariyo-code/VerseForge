"""Portable VerseForge conversation UX: a small menu and truthful, tool-gated handoff.

No host UI, model, auth service or UEFN editor is created or discovered here.
"""
from __future__ import annotations

import re
import unicodedata

MENU = (
    ("create", "Créer un système", "Téléphone, garage, inventaire"),
    ("fix", "Corriger un bug", "Erreurs Verse et gameplay"),
    ("ui", "Créer une interface", "Menu, HUD, UI Verse/UMG"),
    ("optimize", "Optimiser", "Performance et stabilité"),
    ("audit", "Analyser un projet", "Architecture et risques"),
    ("api", "Aide Verse et UEFN", "API, devices et documentation"),
    ("settings", "Paramètres", "Licence et connexion à UEFN"),
)

MODES = {
    "create": "BUILD", "fix": "DEBUG", "ui": "UI", "optimize": "OPTIMIZE",
    "audit": "AUDIT", "api": "API_VERIFY", "settings": "DISCOVERY",
}

_QUESTIONS = {
    "create": "Quel système souhaites-tu créer, et que doit-il faire ?",
    "fix": "Peux-tu fournir le code concerné et le message d'erreur exact ?",
    "ui": "Quelle interface veux-tu et quelles actions doit-elle permettre ?",
    "optimize": "Peux-tu fournir le code ou le projet à optimiser ?",
    "audit": "Quel code ou dossier de projet souhaites-tu analyser ?",
    "api": "Quelle est ta question sur Verse ou UEFN ?",
    "settings": "Veux-tu vérifier la connexion UEFN, l'installation ou la licence ?",
}

_PROMPTS = {
    "create": "Par exemple : garage RP avec récupération des véhicules et menu.",
    "fix": "Tu peux coller l'erreur de compilation et le fichier .verse.",
    "ui": "Par exemple : téléphone RP à deux écrans avec boutons interactifs.",
    "optimize": "Par exemple : boucle Verse lente ou UI qui se met à jour trop souvent.",
    "audit": "Tu peux joindre des fichiers .verse ou autoriser l'accès au projet.",
    "api": "Par exemple : paramètres et effets de button_device.InteractedWithEvent.",
    "settings": "Les licences locales ne prouvent pas l'existence d'un service commercial.",
}

# Rules work on accent-folded, lowercase text. A UI mentioned inside a full system
# request is a supporting requirement, not a reason to switch BUILD to UI.
_PATTERNS = (
    ("fix", r"\b(?:bug|debug|corrig\w*|erreur\w*|repar\w*|fix|crash|compile\w*)\b"),
    ("optimize", r"\b(?:optimis\w*|optimiz\w*|performance\w*|latence|lag\w*)\b"),
    ("audit", r"\b(?:audit\w*|analys\w*|inspection|inspect\w*|review\w*)\b"),
    ("settings", r"\b(?:parametres?|settings?|licen[cs]e\w*|connect\w*|mcp)\b"),
    ("api", r"\b(?:documentation|api|signature|syntaxe|expliqu\w*|aide|help|tutoriel|tutorial|docs?)\b"),
    ("ui", r"\b(?:interface\w*|umg|hud|widget\w*|menu\w*|ui|ecran\w*)\b"),
)
_SYSTEM_VERBS = re.compile(r"\b(?:cre\w*|constru\w*|develop\w*|implemente\w*|fai\w*|systeme\w*)\b")
_SYSTEM_NOUNS = re.compile(r"\b(?:systeme|telephone|garage|inventaire|banque|economie|metier|vehicule|mission|rp)\b")


def _normal(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def classify(request: str) -> dict:
    """Classify a user task. Invocation alone shows the menu, not a workflow."""
    if not isinstance(request, str):
        raise ValueError("Request must be text")
    value = _normal(request)
    if not value or value in ("verseforge", "/verseforge", "$verseforge", "@verseforge"):
        return {"show_menu": True, "intent": None, "mode": None}
    # Explicitly named skill plus a task: route the task instead of displaying a menu.
    value = re.sub(r"^(?:/|\$|@)?verseforge[\s,:-]+", "", value).strip()
    if not value:
        return {"show_menu": True, "intent": None, "mode": None}
    if re.search(r"\b(?:image|capture|screenshot|photo)\b", value) and re.search(
        r"\b(?:recre\w*|reconstitu\w*|refai\w*|reprodui\w*|reverse|interface|ui|hud|verse)\b", value):
        return {"show_menu": False, "intent": "ui", "mode": "UI"}
    for intent, expression in _PATTERNS:
        if re.search(expression, value):
            if intent == "ui" and _SYSTEM_VERBS.search(value) and _SYSTEM_NOUNS.search(value) and not re.search(r"\b(?:cre\w*|fai\w*|develop\w*)\s+(?:une?\s+)?(?:interface|hud|widget|menu|ecran)\b", value):
                return {"show_menu": False, "intent": "create", "mode": MODES["create"]}
            return {"show_menu": False, "intent": intent, "mode": MODES[intent]}
    return {"show_menu": False, "intent": "create", "mode": "BUILD"}


def menu(format: str = "text") -> dict:
    if format not in ("text", "json"):
        raise ValueError("format must be text or json")
    choices = [
        {"id": item_id, "number": number, "label": label, "description": description, "mode": MODES[item_id]}
        for number, (item_id, label, description) in enumerate(MENU, 1)
    ]
    display = "VERSEFORGE — Que veux-tu faire ?\n" + "\n".join(
        f'{item["number"]}. {item["label"]} — {item["description"]}' for item in choices
    ) + "\n\nChoisis un numéro ou décris directement ta demande."
    return {
        "result": "PASS", "view": "control-center", "display": display if format == "text" else None,
        "choices": choices, "interactive_native_panel": "NOT GUARANTEED",
        "note": "Un skill peut fournir un menu textuel ; les boutons natifs dépendent de l'hôte.",
    }


def resolve_choice(selection: str | int) -> str:
    """Resolve numeric or semantic menu selection, without guessing unknown items."""
    if isinstance(selection, bool) or not isinstance(selection, (str, int)):
        raise ValueError("Unknown menu choice")
    value = _normal(str(selection))
    value = re.sub(r"^(?:option|choix|numero|n°|no)\s*", "", value).strip(" .:-")
    if value.isdecimal():
        number = int(value)
        if 1 <= number <= len(MENU):
            return MENU[number - 1][0]
    for item_id, label, _ in MENU:
        if value in (item_id, _normal(label), _normal(MODES[item_id])):
            return item_id
    raise ValueError(f"Unknown menu choice: {selection}")


def route(
    request: str, *, can_create_files: bool = False, can_edit_project: bool = False,
    uefn_connected: bool = False, output: str = "auto",
) -> dict:
    if output not in ("auto", "code", "zip", "project"):
        raise ValueError("Invalid output: auto, code, zip or project")
    selected = classify(request)
    if selected["show_menu"]:
        result = menu()
        result["next_action"] = "Attendre le choix utilisateur sans prétendre avoir implémenté du code."
        return result
    value = _normal(request)
    explicit_zip = bool(re.search(r"\b(?:zip|archive|telecharg\w*|download\w*)\b", value))
    explicit_code = bool(re.search(r"\b(?:juste le code|code dans le chat|code uniquement|inline)\b", value))
    explicit_project = bool(re.search(r"\b(?:projet existant|dans mon projet|modifi\w* mon projet|edit\w* project)\b", value))
    desired = output if output != "auto" else (
        "code" if explicit_code else "zip" if explicit_zip else "project" if explicit_project else "code"
    )
    # Explanatory choices should not instruct the agent to create Verse files by default.
    if output == "auto" and not explicit_zip and not explicit_project and selected["intent"] in ("api", "settings", "audit"):
        desired = "chat"
    effective = desired
    reasons = []
    if desired == "zip" and not can_create_files:
        effective = "code"
        reasons.append("Aucun outil de création de fichiers confirmé : fournir les sources dans le chat.")
    if desired == "project" and not can_edit_project:
        effective = "zip" if can_create_files else "code"
        reasons.append("Aucun accès en écriture au projet confirmé : ne pas prétendre modifier UEFN.")
    if effective == "project" and not uefn_connected:
        reasons.append("Éditeur UEFN non confirmé : compilation et gameplay NOT TESTED.")
    if selected["intent"] == "settings" and output == "auto":
        reasons.append("Le contrôle de licence commercial n'est pas déployé ; ne pas inventer son statut.")
    return {
        "result": "PASS", "view": "task", "intent": selected["intent"], "mode": selected["mode"],
        "requested_output": desired, "selected_output": effective,
        "declared_capabilities": {
            "create_files": bool(can_create_files), "edit_project": bool(can_edit_project),
            "uefn_connected": bool(uefn_connected),
        },
        "caveats": reasons,
        "host_action": {
            "chat": "Agent hôte : répondre dans la conversation avec des informations vérifiables, sans créer de fichiers inutiles.",
            "code": "Agent hôte : écrire des sources Verse complètes dans le chat, fichiers séparés et guide d'intégration.",
            "zip": "Agent hôte : écrire les sources Verse, les placer dans un staging sûr, puis utiliser vf package.",
            "project": "Agent hôte : inspecter le projet autorisé, proposer un diff, appliquer avec sauvegarde et rollback.",
        }[effective],
        "uefn_compile": "NOT TESTED", "gameplay": "NOT TESTED", "multiplayer": "NOT TESTED",
        "not_a_code_generator": True,
    }


def guide(
    choice: str | int | None = None, details: str = "", *, output: str = "auto",
    can_create_files: bool = False, can_edit_project: bool = False,
    uefn_connected: bool = False,
) -> dict:
    """One-step Control Center transition. No persistent user state or fake host session."""
    if choice is None or (isinstance(choice, str) and not choice.strip()):
        return menu()
    intent = resolve_choice(choice)
    if not isinstance(details, str):
        raise ValueError("Task details must be text")
    details = details.strip()
    if not details:
        return {
            "result": "PASS", "view": "question", "intent": intent, "mode": MODES[intent],
            "question": _QUESTIONS[intent], "example": _PROMPTS[intent],
            "next_action": "Ask this one question, then continue with the selected workflow.",
            "needs_user_input": True,
        }
    if len(details) > 32_000:
        raise ValueError("Task details too large")
    if intent == "fix" and not ("\n" in details or re.search(r"\b(?:error|erreur|[0-9]{4})\b", _normal(details))):
        return {
            "result": "PASS", "view": "question", "intent": intent, "mode": MODES[intent],
            "question": _QUESTIONS[intent], "example": _PROMPTS[intent], "needs_user_input": True,
            "note": "Une description seule ne permet pas de corriger le code sans voir le diagnostic ou les sources.",
        }
    result = route(details, output=output, can_create_files=can_create_files,
                   can_edit_project=can_edit_project, uefn_connected=uefn_connected)
    result["intent"] = intent
    result["mode"] = MODES[intent]
    result["view"] = "ready"
    result["question"] = None
    result["next_action"] = (
        "Read only the selected workflow and relevant project context. "
        "The host LLM performs the work; report compile/gameplay honestly."
    )
    result["workflow"] = {
        "create": "workflows/build.md", "fix": "workflows/debug.md",
        "ui": "workflows/ui-design.md", "optimize": "workflows/optimize.md",
        "audit": "workflows/audit.md", "api": "workflows/api-verify.md",
        "settings": "integrations/CHAT_MODE_FR.md",
    }[intent]
    result["user_task"] = details
    return result
