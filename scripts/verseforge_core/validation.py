"""Deterministic structural checks. Not an LLM or UEFN evaluator."""
from __future__ import annotations
import json
import re
from pathlib import Path

NEEDED = ('SKILL.md','workflows/ROUTER.md','workflows/build.md',
 'integrations/UEFN_MCP.md','assets/sources.json','templates/recipes.json',
 'references/validation/EVIDENCE.md','references/ui/ENGINE.md',
 'workflows/chat-mode.md','workflows/control-center.md','integrations/CHAT_MODE_FR.md',
 'workflows/quality-and-delivery.md','workflows/visual-reference.md','integrations/CHATGPT_FR.md')
STATUSES = {'draft','static-checked','compiled','verified','multiplayer-verified'}

def validate(root: Path) -> dict:
    issues=[]
    root=root.resolve(strict=True)
    for file in NEEDED:
        if not (root/file).is_file():
            issues.append(f'Missing required file: {file}')
    skill=root/'SKILL.md'
    if skill.exists():
        content=skill.read_text(encoding='utf-8')
        front=re.match(r'\A---\n(.*?)\n---\n',content,re.S)
        if not front:
            issues.append('Missing YAML frontmatter')
        else:
            fm=front.group(1)
            name=re.search(r'^name:\s*(.+)$',fm,re.M)
            descr=re.search(r'^description:\s*(.+)$',fm,re.M)
            if not name or name.group(1).strip(" '\" ")!='verseforge':
                issues.append('Skill name does not equal verseforge')
            if not descr or len(descr.group(1).strip())>1024:
                issues.append('Invalid/missing skill description')
        if 'TODO(API VERIFY)' not in content:
            issues.append('Missing API verification policy')
    try:
        recipes=json.loads((root/'templates/recipes.json').read_text())
        required={'id','objective','dependencies','interfaces','api_requirements','limitations','acceptance_tests','validation'}
        ids=set()
        for r in recipes:
            if not required.issubset(r):issues.append(f'Incomplete recipe: {r.get("id")}')
            if r.get('validation') not in STATUSES:issues.append(f'Invalid recipe status: {r.get("id")}')
            if r['id'] in ids:issues.append(f'Duplicate recipe: {r["id"]}')
            ids.add(r['id'])
    except (OSError,ValueError,KeyError,TypeError) as e:
        issues.append(f'Invalid recipes: {e}')
        recipes=[]
    try:
        sources=json.loads((root/'assets/sources.json').read_text())
        for s in sources:
            if not s['url'].startswith('https://') or 'license' not in s or 'redistribution' not in s:
                issues.append('Bad asset source entry')
    except (OSError,ValueError,KeyError,TypeError) as e:
        issues.append(f'Invalid asset sources: {e}')
        sources=[]
    for p in root.rglob('*'):
        if p.is_symlink():issues.append(f'Symlink not allowed in distributable: {p}')
        if p.is_file() and p.suffix.lower() in ('.pem','.key','.p12','.env'):
            issues.append(f'Possible private secret file: {p.relative_to(root)}')
    return {'result':'PASS' if not issues else 'FAIL','issue_count':len(issues),'issues':issues,
            'recipe_count':len(recipes),'asset_source_count':len(sources),'verse_compile':'NOT TESTED'}
