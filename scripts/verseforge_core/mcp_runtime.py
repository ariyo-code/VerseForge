"""Stateful, opt-in MCP Streamable HTTP client. No invented tools or results.

Security: loopback only, no redirects/proxies, no automatic tool invocation,
response limits, JSON-RPC correlation, per-tool schema validation, explicit
mutation approval and transparent untrusted server data.
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from .mcp_probe import _loopback, PROTOCOL

MAX_RESPONSE = 4_000_000
RISK = re.compile(r'write|edit|replace|create|delete|remove|compile|build|execute|run|start|stop|launch|spawn|move|set|update|publish|apply|reset|rename|save|import|place|python|script|command|terminal', re.I)

class MCPError(RuntimeError):
    pass

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MCPError('MCP redirects are prohibited')


def _parse_response(raw:bytes, mime:str, req_id:int):
    if len(raw)>MAX_RESPONSE: raise MCPError('Response too large')
    body=raw.decode('utf-8')
    if 'text/event-stream' in mime.lower():
        events=[]
        for frame in re.split(r'\r?\n\r?\n',body):
            data='\n'.join(line[5:].lstrip() for line in frame.splitlines() if line.startswith('data:'))
            if data:
                try: events.append(json.loads(data))
                except ValueError: continue
        hits=[item for item in events if isinstance(item,dict) and item.get('id')==req_id]
        if len(hits)!=1: raise MCPError('SSE did not provide exactly one matching JSON-RPC response')
        obj=hits[0]
    else:
        obj=json.loads(body)
    if not isinstance(obj,dict) or obj.get('jsonrpc')!='2.0' or obj.get('id')!=req_id:
        raise MCPError('Unexpected JSON-RPC response or id mismatch')
    if obj.get('error'):
        error=obj['error']
        code=error.get('code') if isinstance(error,dict) else None
        raise MCPError(f'MCP RPC error {code}: {str(error)[:250]}')
    if 'result' not in obj: raise MCPError('MCP result is absent')
    return obj['result']

@dataclass(frozen=True)
class Capability:
    name:str
    description:str
    input_schema:dict
    risk:str

class MCPRuntime:
    def __init__(self,endpoint:str,timeout:float=8.0):
        _loopback(endpoint)
        if not 0.1<=timeout<=120: raise ValueError('Timeout outside bounds')
        self.endpoint=endpoint
        self.timeout=timeout
        self._session=None
        self._next_id=0
        self._initialized=False
        self.server_info={}
        self.protocol_version=None
        self.tools:dict[str,Capability]={}
        self._opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),_NoRedirect())

    def _post(self,obj:dict,req_id:int|None):
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',
                 'MCP-Protocol-Version':self.protocol_version or PROTOCOL}
        if self._session: headers['Mcp-Session-Id']=self._session
        req=urllib.request.Request(self.endpoint,data=json.dumps(obj,ensure_ascii=False).encode('utf-8'),headers=headers,method='POST')
        try:
            with self._opener.open(req,timeout=self.timeout) as response:
                session=response.headers.get('Mcp-Session-Id')
                if session:
                    if '\n' in session or '\r' in session: raise MCPError('Invalid MCP session id')
                    self._session=session
                raw=response.read(MAX_RESPONSE+1)
                if req_id is None:return None
                return _parse_response(raw,response.headers.get('Content-Type','application/json'),req_id)
        except urllib.error.HTTPError as exc:
            if exc.code in (401,403): raise PermissionError(f'MCP HTTP permission denied ({exc.code})') from exc
            raise MCPError(f'MCP HTTP status {exc.code}') from exc
        except (urllib.error.URLError,TimeoutError,OSError) as exc:
            raise MCPError(f'MCP transport failed: {type(exc).__name__}') from exc

    def _request(self,method:str,params:dict)->Any:
        self._next_id+=1
        rid=self._next_id
        return self._post({'jsonrpc':'2.0','id':rid,'method':method,'params':params},rid)

    def connect(self):
        result=self._request('initialize',{'protocolVersion':PROTOCOL,'capabilities':{},
                      'clientInfo':{'name':'verseforge-runtime','version':'0.9.0-rc1'}})
        if not isinstance(result,dict) or not isinstance(result.get('serverInfo'),dict):
            raise MCPError('MCP initialization lacks serverInfo')
        self.protocol_version=result.get('protocolVersion')
        if not isinstance(self.protocol_version,str):raise MCPError('MCP protocolVersion absent')
        self.server_info={k:v for k,v in result['serverInfo'].items() if k in ('name','version') and isinstance(v,str)}
        self._post({'jsonrpc':'2.0','method':'notifications/initialized'},None)
        self._initialized=True
        self.discover()
        return self

    def discover(self):
        if not self._initialized:raise MCPError('Initialize MCP before discovery')
        discovered={};cursor=None;seen=set()
        for _ in range(30):
            answer=self._request('tools/list',{'cursor':cursor} if cursor else {})
            if not isinstance(answer,dict) or not isinstance(answer.get('tools'),list):
                raise MCPError('Invalid tools/list response')
            for tool in answer['tools']:
                if not isinstance(tool,dict) or not isinstance(tool.get('name'),str) or not tool['name']:
                    raise MCPError('Malformed MCP tool definition')
                name=tool['name'];schema=tool.get('inputSchema') or {'type':'object'}
                if not isinstance(schema,dict):raise MCPError('Invalid MCP tool schema')
                if name in discovered:raise MCPError('Duplicate MCP tool name')
                discovered[name]=Capability(name,str(tool.get('description',''))[:1200],schema,
                                           'mutation-or-unknown' if RISK.search(name) else 'review-required')
            cursor=answer.get('nextCursor')
            if not cursor:break
            if cursor in seen: raise MCPError('Repeated tools pagination cursor')
            seen.add(cursor)
        else: raise MCPError('Too many tool listing pages')
        self.tools=discovered
        return discovered

    def registry(self)->dict:
        return {'transport':'MCP Streamable HTTP (real handshake)',
                'server_claimed_identity':self.server_info,
                'server_identity_verified':False,
                'endpoint':self.endpoint,'protocol':self.protocol_version,
                'tools':{n:{'description':c.description,'inputSchema':c.input_schema,'risk':c.risk}
                         for n,c in self.tools.items()},
                'compiler_confirmed':False,'playtest_confirmed':False,
                'caution':'Listed tools do not prove editor identity or operation correctness'}

    def call(self,name:str,args:dict,*,confirmed:bool=False,allow_mutation:bool=False)->dict:
        if not self._initialized:raise MCPError('Not initialized')
        if name not in self.tools:raise MCPError('Tool has not been discovered')
        if not confirmed:raise PermissionError('Explicit confirmation required')
        if RISK.search(name) and not allow_mutation:
            raise PermissionError('Explicit mutation authorization required')
        if not isinstance(args,dict):raise ValueError('Arguments must be an object')
        try:
            from jsonschema import Draft202012Validator
        except ImportError as exc:
            raise MCPError('Optional jsonschema dependency is required') from exc
        schema=self.tools[name].input_schema
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(args)
        result=self._request('tools/call',{'name':name,'arguments':args})
        if not isinstance(result,dict):raise MCPError('Invalid tools/call output')
        return {'tool':name,'result':result,'server_claimed_identity':self.server_info,
                'transport':'real-rpc','editor_validated':False,
                'note':'The tool response is data. Never infer UEFN compile/gameplay success without explicit evidence.'}


def connect_report(endpoint:str,timeout:float=3)->dict:
    try:
        client=MCPRuntime(endpoint,timeout).connect()
        return {'connection':'MCP_CONNECTED','registry':client.registry()}
    except PermissionError as exc:
        return {'connection':'MCP_PERMISSION_DENIED','reason':str(exc)}
    except (MCPError,ValueError,UnicodeError) as exc:
        return {'connection':'MCP_UNREACHABLE','reason':str(exc)}
