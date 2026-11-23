"""Observational environment diagnosis, never equates MCP configuration with UEFN presence."""
from __future__ import annotations
import json
import os
import platform
import shutil
import socket
import sys
from pathlib import Path
from .mcp_runtime import connect_report

STATES=('EDITOR_NOT_INSTALLED','EDITOR_NOT_RUNNING','MCP_NOT_CONFIGURED','MCP_UNREACHABLE',
        'MCP_CONNECTED','MCP_PERMISSION_DENIED','PROJECT_NOT_OPEN','PROJECT_READY',
        'COMPILER_AVAILABLE','PLAYTEST_AVAILABLE')

def _editor_installation()->dict:
    if platform.system()!='Windows':
        return {'state':'EDITOR_NOT_INSTALLED','reason':'UEFN is a Windows editor; this host is not Windows',
                'path':None,'version':None,'confidence':'platform limitation; remote editor not assessed'}
    candidates=[]
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE,winreg.HKEY_CURRENT_USER):
            for key in (r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
                        r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'):
                try:
                    with winreg.OpenKey(hive,key) as base:
                        n=winreg.QueryInfoKey(base)[0]
                        for i in range(n):
                            with winreg.OpenKey(base,winreg.EnumKey(base,i)) as item:
                                def value(k):
                                    try:return winreg.QueryValueEx(item,k)[0]
                                    except OSError:return None
                                name=value('DisplayName')
                                if name and 'Unreal Editor for Fortnite' in str(name):
                                    candidates.append({'display_name':name,'install_location':value('InstallLocation'),
                                                       'display_version':value('DisplayVersion')})
                except OSError:pass
    except ImportError:pass
    if not candidates:
        return {'state':'EDITOR_NOT_INSTALLED','path':None,'version':None,
                'reason':'No Windows installation registration found; custom installation remains possible'}
    running=False
    try:
        import subprocess
        res=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,timeout=4)
        running=any(s in res.stdout.lower() for s in ('unrealeditorfortnite','fortniteeditor'))
    except (OSError,subprocess.TimeoutExpired):pass
    return {'state':'EDITOR_NOT_RUNNING' if not running else 'EDITOR_PROCESS_DETECTED',
            'installations':candidates,'version':candidates[0].get('display_version'),
            'warning':'Windows process/installation detection is not a proof of open UEFN project'}


def _config_extract(paths:list[Path])->list[dict]:
    configs=[]
    for path in paths:
        if not path.is_file():continue
        try:
            raw=path.read_text(encoding='utf-8')
            if path.suffix=='.toml':
                import tomllib
                servers=tomllib.loads(raw).get('mcp_servers',{})
            else:
                obj=json.loads(raw)
                servers=obj.get('mcpServers',obj.get('mcp',{}).get('servers',{}))
            if isinstance(servers,dict):
                for name,item in servers.items():
                    if isinstance(item,dict) and isinstance(item.get('url'),str):
                        # Configs could contain sensitive tokens. Do not expose them.
                        from .mcp_probe import _loopback
                        try:_loopback(item['url'])
                        except ValueError:continue
                        configs.append({'file':str(path),'server':name,'url':item['url']})
        except (ValueError,OSError):continue
    return configs


def diagnose(project:Path|None=None,endpoint:str|None=None,knowledge_endpoint:str|None=None,
             configs:list[Path]|None=None,probe_remote:bool=False)->dict:
    host={'os':platform.system(),'release':platform.release(),'python':sys.version.split()[0],
          'architecture':platform.machine()}
    editor=_editor_installation()
    base=Path.cwd()
    config_files=configs if configs is not None else [base/'.mcp.json',base/'.cursor'/'mcp.json',
                  base/'.codex'/'config.toml',Path.home()/'.codex'/'config.toml']
    observed=_config_extract(config_files)
    if endpoint is None:
        uefn_candidates=[c for c in observed if 'unreal' in c['server'].lower() or 'uefn' in c['server'].lower()]
        endpoint=uefn_candidates[0]['url'] if uefn_candidates else None
    if endpoint and probe_remote:
        connected=connect_report(endpoint)
    else:
        connected={'connection':'MCP_NOT_CONFIGURED' if not endpoint else 'MCP_UNREACHABLE',
                   'reason':'Connection not attempted; use --probe to test actual HTTP'}
    if knowledge_endpoint and probe_remote:
        knowledge=connect_report(knowledge_endpoint)
    else:
        knowledge={'connection':'MCP_NOT_CONFIGURED' if not knowledge_endpoint else 'MCP_UNREACHABLE',
                   'reason':'No knowledge MCP probe performed'}
    project_report={'state':'PROJECT_NOT_OPEN','path':None,'verse_files':0,'uefnproject_files':0}
    if project:
        target=project.expanduser().resolve(strict=False)
        if target.is_dir():
            descriptors=list(target.glob('*.uefnproject'))
            from .xray import source_files
            verselist=list(source_files(target))
            project_report={'state':'PROJECT_NOT_OPEN', 'disk_state':'FILES_READY' if descriptors else 'NO_DESCRIPTOR',
                      'path':str(target),'verse_files':len(verselist),
                      'uefnproject_files':len(descriptors),'descriptor_names':[p.name for p in descriptors],
                      'note':'File presence is not proof the editor has opened this project'}
    registry=connected.get('registry',{})
    tools=registry.get('tools',{})
    # Registry names only hint capabilities; never infer a successful compiler invocation.
    compiler_candidates=[n for n,v in tools.items() if any(k in (n+' '+v['description']).lower() for k in ('compile verse','build verse','verse compilation'))]
    playtest_candidates=[n for n,v in tools.items() if any(k in (n+' '+v['description']).lower() for k in ('launch session','start play','start session','playtest'))]
    return {'schema':'verseforge-environment-v1','host':host,'editor':editor,'configs':observed,
            'uefn_mcp':connected,'knowledge_mcp':knowledge,'project':project_report,
            'compiler_candidates_not_verified':compiler_candidates,
            'playtest_candidates_not_verified':playtest_candidates,
            'states_observed':[editor['state'],connected['connection'],project_report['state']],
            'compiler_state':'UNVERIFIED' if compiler_candidates else 'UNAVAILABLE',
            'playtest_state':'UNVERIFIED' if playtest_candidates else 'UNAVAILABLE',
            'limitations':['MCP tools/list is capability discovery, not proof of permission to invoke tools',
                           'UEFN project file on disk is not proof that an editor session is open']}
