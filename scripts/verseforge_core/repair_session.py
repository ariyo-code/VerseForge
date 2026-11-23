"""Bounded compiler-driven repair orchestration; repairs are authored by a coding agent.

Inputs must be complete hash-preconditioned proposals. No synthetic fixes or fallback
compiler. Every compile attempt must return a real observed result or UNAVAILABLE.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Callable
from .build import verify_proposal
from .workspace import rollback
from .repair import next_attempt


def _fingerprint(candidate:dict)->str:
    return hashlib.sha256(json.dumps(candidate,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def _errors(result:dict):
    return {((d.get('file') or ''),d.get('line'),d.get('message') or '') for d in result.get('diagnostics',[])
            if d.get('severity')=='error'}

def run_repair_session(project:Path,baseline:dict,candidates:list[dict],compiler:Callable[[],dict],
                       *,max_attempts:int=3)->dict:
    """Only executes with an injected real compiler adapter or a marked test mock.

    Candidate proposals must have been authored independently and verified against
    the current project by the existing Workspace Editor. Stop instead of guessing.
    """
    if not 1<=max_attempts<=10:raise ValueError('Maximum attempts outside bounds')
    if not isinstance(candidates,list):raise ValueError('Expected ordered agent proposals')
    if baseline.get('status')!='FAILED':
        return {'result':'STOP','reason':'A confirmed FAILED baseline is required','attempts':[]}
    root=project.expanduser().resolve(strict=True)
    history=[]; current=baseline
    seen=set()
    for plan in candidates[:max_attempts]:
        sha=_fingerprint(plan)
        if sha in seen:return {'result':'STOP','reason':'Repeated correction proposal','attempts':history}
        seen.add(sha)
        allowance=next_attempt([{'candidate_sha256':x['candidate_sha256']} for x in history],sha,max_attempts)
        if allowance['result']!='PROPOSE':return {'result':'STOP','reason':allowance['reason'],'attempts':history}
        # Validate every proposal before mutating. The agent must inspect affected APIs.
        preview=verify_proposal(root,plan,apply=False)
        if preview['result']!='PREVIEW':
            return {'result':'STOP','reason':'Proposal failed preview/static review','attempts':history,'preview':preview}
        applied=verify_proposal(root,plan,apply=True)
        if applied['result']!='APPLIED':
            return {'result':'STOP','reason':'Proposal application was refused','attempts':history}
        batch=applied['changes']['backup_batch']
        try:
            updated=compiler()
            if not isinstance(updated,dict) or updated.get('status') not in ('SUCCESS','FAILED','UNKNOWN','UNAVAILABLE','TIMEOUT','CANCELLED'):
                raise ValueError('Compiler returned invalid result contract')
        except Exception:
            rollback(root,batch)
            raise
        status=updated['status']
        before=_errors(current);after=_errors(updated)
        introduced=sorted(str(e) for e in (after-before))
        original_count=current.get('error_count')
        current_count=updated.get('error_count')
        # A new diagnostic does not always mean worse; refuse unsafe progress.
        worsening=(status!='SUCCESS' and (introduced or
                   (isinstance(original_count,int) and isinstance(current_count,int) and current_count>original_count)))
        blocked=status in ('UNKNOWN','UNAVAILABLE','TIMEOUT','CANCELLED')
        no_progress=(status=='FAILED' and after==before and current_count==original_count)
        inconsistent_success=(status=='SUCCESS' and bool(after))
        row={'candidate_sha256':sha,'backup_batch':batch,'compile_run_id':updated.get('run_id'),
             'compile_status':status,'previous_errors':original_count,'new_errors':current_count,
             'new_diagnostics':introduced,'rollback':False}
        if worsening or blocked or no_progress or inconsistent_success:
            rollback(root,batch);row['rollback']=True;history.append(row)
            return {'result':'STOP','reason':('Unverified compilation' if blocked or inconsistent_success else
                                               'No diagnostic improvement' if no_progress else 'Regression detected'),
                    'attempts':history,'last_compile':updated}
        history.append(row)
        current=updated
        if status=='SUCCESS':
            return {'result':'COMPILED_RESPONSE_REPORTED','attempts':history,'last_compile':current,
                    'warning':'Editor origin still requires independent confirmation; runtime untested'}
    return {'result':'STOP','reason':'Attempt budget exhausted or no more agent proposals',
            'attempts':history,'last_compile':current}
