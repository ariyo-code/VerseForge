"""Field-by-field API evidence gate, delegated to upstream verse-ai claim resolver.
A local proof ledger may record links, but cannot silently elevate upstream claim denials.
"""
from __future__ import annotations
import json
from .knowledge import run_knowledge
FIELDS=('presence','module','signature','parameters','return_type','effects','event_payloads')


def check_claims(symbols:list[str],repo:str|None=None,runner=run_knowledge,fields:tuple[str,...]=FIELDS)->dict:
    if len(symbols)>100:raise ValueError('Too many symbols in one claim batch')
    if not fields or any(field not in FIELDS for field in fields):raise ValueError('Invalid claim fields')
    output=[];passed=True
    for symbol in symbols:
        if not isinstance(symbol,str) or not symbol.strip() or len(symbol)>160 or not all(c.isalnum() or c in '._/' for c in symbol):
            raise ValueError('Invalid symbol')
        claims={}
        for field in fields:
            reply=runner(['claim',symbol,'--field',field,'--json'],repo)
            if not reply.get('available') or reply.get('status')!='PASS':
                claims[field]={'decision':'TODO(API VERIFY)','reason':reply.get('reason') or 'Upstream claim evidence not available'}
                passed=False
                continue
            try:
                obj=json.loads(reply['stdout'])
                allowed=obj.get('decision')=='ALLOW' and obj.get('supported') is True
                claims[field]={'decision':'ALLOW' if allowed else 'TODO(API VERIFY)',
                               'evidence_ids':obj.get('evidence_ids',[]),'reason':obj.get('reason','')}
                if not allowed:passed=False
            except (ValueError,KeyError,TypeError):
                claims[field]={'decision':'TODO(API VERIFY)','reason':'Invalid upstream JSON'};passed=False
        output.append({'symbol':symbol,'claims':claims})
    return {'result':'PASS' if passed else 'NEEDS_API_VERIFICATION','source':'verse-ai field claim resolver',
            'symbols':output,'compiler':'NOT TESTED'}
