"""Evidence-preserving correction-session ledger; agent proposes edits, not guesses."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

DIAG=re.compile(r'(?P<file>[^\s:]+\.verse)(?:\((?P<line_a>\d+)\s*,\s*(?P<col_a>\d+)\)|:(?P<line_b>\d+)(?::(?P<col_b>\d+))?)')


def classify(log:str)->dict:
    if not log.strip():raise ValueError('Compiler output required')
    items=[]
    for line in log.splitlines():
        if not any(word in line.casefold() for word in ('error','failed','warning','erreur')):continue
        m=DIAG.search(line)
        items.append({'exact_message':line[:2000], 'file':m.group('file') if m else None,
                      'line':int(m.group('line_a') or m.group('line_b')) if m else None,
                      'category':'api-or-typing' if any(s in line.casefold() for s in ('unknown identifier','no overload','type error')) else 'compiler-diagnostic'})
    return {'source':'user-provided-compiler-log','compiler_result':'FAILED (reported; not independently verified)',
            'log_sha256':hashlib.sha256(log.encode()).hexdigest(),'diagnostics':items}


def next_attempt(history:list[dict],candidate_sha256:str,max_attempts:int=3)->dict:
    if not re.fullmatch(r'[0-9a-f]{64}',candidate_sha256):raise ValueError('Invalid candidate hash')
    if not 1<=max_attempts<=20:raise ValueError('Invalid maximum attempts')
    if len(history)>=max_attempts:return {'result':'STOP','reason':'Maximum attempts reached'}
    if any(x.get('candidate_sha256')==candidate_sha256 for x in history):
        return {'result':'STOP','reason':'Repeated correction candidate'}
    return {'result':'PROPOSE','attempt':len(history)+1,'max_attempts':max_attempts,
            'instruction':'Apply minimally with hash preconditions; recompile in UEFN and attach exact output'}
