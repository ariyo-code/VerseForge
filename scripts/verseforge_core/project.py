"""Bounded, side-effect free project discovery and deterministic planning."""
from __future__ import annotations
import json
import re
from pathlib import Path

DOMAINS = {
    'garage': ('garage', 'garages', 'parking'),
    'economy': ('bank', 'banque', 'economie', 'économie', 'argent', 'transaction', 'achat', 'buy', 'currency'),
    'vehicles': ('vehicle', 'véhicule', 'voiture', 'car', 'concession'),
    'persistence': ('persist', 'save', 'sauvegarde'),
    'ui': ('ui', 'interface', 'umg', 'menu', 'hud', 'phone', 'téléphone'),
    'multiplayer': ('multi', 'joueurs', 'players', 'réseau', 'server'),
    'factions': ('faction', 'police', 'mdt', 'organisation', 'staff'),
    'combat': ('dégât', 'damage', 'combat', 'weapon'),
}
RECIPE_DEPS = {
    'garage': ['vehicles','economy','persistence'],
    'economy': ['player-state'],
    'vehicles': ['player-state'],
    'factions': ['permissions','player-state'],
}
# Scanning safety caps. No file execution, content collection or symlink traversal.
MAX_FILES = 1200
MAX_TEXT_BYTES = 256_000


def inspect_project(path: Path) -> dict:
    root = path.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Project must be a directory')
    verse=[]; projects=[]; note=[]; truncated=False
    for p in root.rglob('*'):
        if p.is_symlink() or not p.is_file() or any(x in ('.git','node_modules','__pycache__') for x in p.relative_to(root).parts):
            continue
        rel=p.relative_to(root).as_posix()
        if p.suffix.lower()=='.verse':
            verse.append(rel)
        elif p.suffix.lower()=='.uefnproject':
            projects.append(rel)
        elif p.name in ('AGENTS.md','CLAUDE.md','README.md'):
            note.append(rel)
        if len(verse)+len(projects)+len(note)>=MAX_FILES:
            truncated=True
            break
    return {'root':str(root),'uefn_projects':sorted(projects),'verse_files':sorted(verse),'project_guidance':sorted(note),'truncated':truncated,'source':'filesystem-inspection','uefn_compilation':'NOT TESTED'}


def build_plan(request: str, project: dict | None = None) -> dict:
    request=request.strip()
    if not request:
        raise ValueError('Request must not be empty')
    s=request.casefold()
    domains=[k for k,words in DOMAINS.items() if any(w in s for w in words)]
    req=set(domains)
    for d in domains:
        req.update(RECIPE_DEPS.get(d,[]))
    risks=[]
    if 'garage' in req:
        risks += ['Confirm vehicle model support in installed UEFN; no assumed save/spawn API','Define currency source and single idempotent purchase authority']
    if 'persistence' in req:
        risks += ['Validate persisting types, size limits and migration compatibility before writes']
    if 'ui' in req:
        risks += ['Verify UMG/Verse UI interaction and controller/touch behavior in editor']
    if 'multiplayer' in req or 'garage' in req:
        risks += ['Test concurrent interactions, player leave, reconnect and respawn with multiple real clients']
    return {'product':'VerseForge','mode':'BUILD','request':request,'domains':domains,'required_services':sorted(req),'acceptance_criteria':['API claims resolved with field-level evidence or TODO(API VERIFY)','No duplicate state owner','Record actual static, compilation, runtime and multiplayer evidence'], 'risks':risks,'project':project,'next_actions':['inspect existing module owners','resolve exact API symbols','implement small reversible vertical slice','compile only using discovered UEFN tools'],'validation':'draft','compiler':'NOT TESTED','runtime':'NOT TESTED','multiplayer':'NOT TESTED'}
