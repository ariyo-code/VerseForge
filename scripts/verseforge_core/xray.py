"""Read-only, bounded Verse structure index. Heuristic analysis, not a Verse parser."""
from __future__ import annotations
import hashlib
import os
import re
from pathlib import Path

IGNORE={'.git','.venv','venv','node_modules','__pycache__','Intermediate','Saved','Binaries','.verseforge'}
CLASS=re.compile(r'(?m)^\s*([A-Za-z][\w]*)\s*:=\s*class(?:<[^>\n]+>)*\s*(?:\([^\n]*\))?\s*:')
IMPORT=re.compile(r'(?m)^\s*using\s*\{\s*([^}]+)\s*\}')
METHOD=re.compile(r'(?m)^\s*([A-Za-z][\w]*)\s*(?:<[^\n>]+>)?\s*\([^\n]*\)\s*(?:<[^\n>]+>)?\s*:\s*[^\n=]+\s*=')
DEVICE=re.compile(r'(?m)^\s*@editable\s*\n\s*([\w]+)\s*:\s*([\w]+)')
EVENT=re.compile(r'([A-Za-z][\w]*)\.([A-Za-z][\w]*(?:Event|OnClick))(?:\(\))?\.Subscribe\s*\(\s*([\w]+)')
WEAK=re.compile(r'(?m)^\s*var\s+([\w]+)(?:<[^>]+>)?\s*:\s*weak_map\s*\(\s*(player|session)\s*,\s*([^\)]+)\)')
MAP=re.compile(r'(?m)^\s*var\s+([\w]+)\s*:\s*\[\s*(?:player|agent)\s*\]')
MAX_BYTES=500_000
MAX_FILES=1200


def source_files(root:Path):
    count=0
    for parent, dirs, files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in IGNORE and not (Path(parent)/d).is_symlink())
        for name in sorted(files):
            path=Path(parent)/name
            if path.is_symlink() or path.suffix.lower()!='.verse':continue
            count+=1
            if count>MAX_FILES:
                raise ValueError('Project exceeds file inspection limit; narrow the project scope')
            yield path


def _neutralize_comments(content:str)->str:
    # Comments are not executable code. Only strip # to line-end; this cannot be a full Verse parser.
    return re.sub(r'(?m)#.*$', '', content)


def analyze_source(path:str, content:str, digest:str|None=None)->dict:
    filtered=_neutralize_comments(content)
    imp=sorted(set(x.strip() for x in IMPORT.findall(filtered)))
    classes=sorted(set(CLASS.findall(filtered)))
    methods=sorted(set(METHOD.findall(filtered)))
    edit=[{'name':n,'type':t} for n,t in DEVICE.findall(filtered)]
    subs=[{'owner':o,'event':e,'handler':h} for o,e,h in EVENT.findall(filtered)]
    wm=[{'name':n,'scope':scope,'value_type':t.strip()} for n,scope,t in WEAK.findall(filtered)]
    player_maps=sorted(set(MAP.findall(filtered)))
    return {'path':path,'sha256':digest or hashlib.sha256(content.encode()).hexdigest(),
            'imports':imp,'classes':classes,'functions':methods,'editable':edit,
            'subscriptions':subs,'weak_maps':wm,'player_maps':player_maps,
            'line_count':content.count('\n')+1,'todo_api_verify':'TODO(API VERIFY)' in content}


def project_xray(root:Path)->dict:
    root=root.expanduser().resolve(strict=True)
    if not root.is_dir(): raise ValueError('Project must be a directory')
    entries=[]; warnings=[]; all_classes={}; all_maps={}
    for path in source_files(root):
        rel=path.relative_to(root).as_posix()
        if path.stat().st_size>MAX_BYTES:
            warnings.append(f'Oversized Verse file not inspected: {rel}');continue
        raw=path.read_bytes()
        try: data=raw.decode('utf-8')
        except UnicodeDecodeError:
            warnings.append(f'Non-UTF8 Verse file skipped: {rel}');continue
        row=analyze_source(rel,data,hashlib.sha256(raw).hexdigest())
        entries.append(row)
        for c in row['classes']:all_classes.setdefault(c,[]).append(rel)
        for m in row['weak_maps']:all_maps.setdefault(m['name'],[]).append(rel)
    for name,owners in sorted(all_classes.items()):
        if len(owners)>1:warnings.append(f'Duplicate class declaration {name}: {owners}')
    for name,owners in sorted(all_maps.items()):
        if len(owners)>1:warnings.append(f'Duplicate weak_map declaration {name}: {owners}')
    economy_hints=[e['path'] for e in entries if any(any(key in c.lower() for key in ('bank','econom','currency','wallet','money')) for c in e['classes']+e['functions'])]
    persistent=[{'file':e['path'],**m} for e in entries for m in e['weak_maps'] if m['scope']=='player']
    return {'root':str(root),'method':'heuristic-read-only','compiler':'NOT TESTED',
            'files':entries,'file_count':len(entries),'classes':all_classes,
            'persistent_maps':persistent,'persistent_map_count':len(persistent),
            'potential_economy_owners':economy_hints,'warnings':warnings,
            'limitations':['Regex-based structural extraction, not a syntax tree or proof of correctness',
                           'Cannot infer editor-only device bindings, UMG assets or runtime topology']}
