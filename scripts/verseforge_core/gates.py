"""Evidence-tier promotions; never infer UEFN build success from Python or mock results."""
from __future__ import annotations
import re
LEVELS=['draft','static-checked','compiled','verified','multiplayer-verified']
REQUIRED={'static-checked':'static_report','compiled':'uefn_compile_log',
          'verified':'gameplay_test_record','multiplayer-verified':'multiplayer_test_record'}


def promote(current:str,target:str,evidence:dict)->dict:
    if current not in LEVELS or target not in LEVELS:raise ValueError('Invalid status')
    ci=LEVELS.index(current); ti=LEVELS.index(target)
    if ti<ci or ti>ci+1:raise ValueError('Only one forward transition at a time')
    if ti==ci:return {'status':current,'promoted':False}
    key=REQUIRED[target]
    proof=evidence.get(key)
    if not isinstance(proof,dict) or not proof.get('success') or not proof.get('source') or not proof.get('timestamp'):
        raise ValueError(f'{target} requires positive real evidence: {key}')
    if target!='static-checked' and (proof.get('source_type') not in {'uefn-editor','pic-session','multi-client-session'} or not proof.get('raw_log_sha256')):
        raise ValueError('Real UEFN/PIC evidence and raw log SHA-256 required')
    if target=='compiled' and proof['source_type']!='uefn-editor':raise ValueError('UEFN compile evidence required')
    if target=='verified' and proof['source_type']!='pic-session':raise ValueError('PIC gameplay evidence required')
    if target=='multiplayer-verified' and proof['source_type']!='multi-client-session':raise ValueError('Multiple clients required')
    if target=='multiplayer-verified' and proof.get('client_count',0)<2:raise ValueError('2+ real clients required')
    return {'status':target,'promoted':True,'evidence_key':key}


def static_review(filename:str,content:str)->dict:
    issues=[]; warnings=[]
    if not filename.endswith('.verse'):issues.append('Not a Verse file')
    if not re.search(r'(?m)^\s*(?:\w+\s*:=\s*(?:class|module)\b|var\s+\w+\s*:|\w+\s*\([^\n]*\)\s*(?:<[^>]+>)*\s*:[^\n=]+\s*=)',content):issues.append('No recognizable Verse declaration')
    if 'TODO(API VERIFY)' in content:warnings.append('Unresolved API verification marker')
    if 'OnBegin' in content and not re.search(r'using\s*\{\s*/Verse\.org/Simulation\s*\}',content):
        warnings.append('OnBegin with no Simulation import: review')
    if 'InteractedWithEvent' in content and 'Subscribe(' not in content: warnings.append('Event present without a subscription')
    if 'weak_map(player' in content and 'persistable' not in content: warnings.append('Review weak_map value type and persistence')
    if re.search(r'(?mi)^\s*#\s*(?:(?:uefn\s+)?compil(?:ed|e)\s*[:=]\s*(?:success|passed|true)|build\s+success)\b',content):
        warnings.append('Do not infer compilation from comments')
    if '\x00' in content:issues.append('Invalid NUL byte')
    return {'file':filename,'syntax_heuristics':'PASS' if not issues else 'FAIL',
            'issues':issues,'warnings':warnings,'uefn_compile':'NOT TESTED',
            'disclaimer':'Lightweight heuristic review; NOT the Verse compiler'}
