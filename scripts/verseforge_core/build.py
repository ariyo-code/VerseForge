"""Agent-to-workspace handoff: capability-aware proposal & controlled edit application.
The LLM must author the Verse content; these tools DO NOT impersonate an LLM.
"""
from __future__ import annotations
import json
from pathlib import Path
from .project import build_plan
from .xray import project_xray
from .gates import static_review
from .workspace import edit_project


def prepare(request:str,project:Path)->dict:
    snapshot=project_xray(project)
    plan=build_plan(request)
    return {'kind':'verseforge-agent-context-v1','goal':request,'plan':plan,'project_xray':snapshot,
            'agent_protocol':['Read existing files selectively; never duplicate named owners',
              'Use verse-ai claim for signature, parameters, return_type, effects and payloads',
              'Document missing evidence with TODO(API VERIFY); do not invent APIs',
              'Generate full .verse sources and a verseforge-edits-v1 plan',
              'Preview every edit and preserve existing owners; only apply after authorization',
              'Run static gate, then UEFN MCP compile only when actually connected'],
            'compiler':'NOT TESTED'}


def verify_proposal(project:Path,proposal:dict,apply=False)->dict:
    if proposal.get('schema')!='verseforge-edits-v1':raise ValueError('Wrong proposal schema')
    checks=[static_review(x['path'],x['new_content']) for x in proposal.get('changes',[])]
    if any(x['syntax_heuristics']!='PASS' for x in checks):
        return {'result':'BLOCKED','reason':'Static heuristic error','reviews':checks}
    changes=edit_project(project,proposal,apply=apply)
    return {'result':changes['result'],'changes':changes,'reviews':checks,
            'api_verification':'EXTERNAL EVIDENCE REQUIRED','compile':'NOT TESTED'}
