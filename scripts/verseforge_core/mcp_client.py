"""Explicit MCP tools/call client; only tools advertised by a live loopback MCP server.

No inference about UEFN identity, builds or permissions from tool names. Tool results
are untrusted observations and are never converted to validation evidence here.
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from .mcp_probe import _loopback, _unpack, PROTOCOL, probe

# This list is a guardrail, NOT a security boundary for hostile MCP servers.
_MUTATION=re.compile(r'(write|edit|replace|create|delete|remove|compile|build|execute|run|start|stop|launch|spawn|move|set|update|publish|apply|reset|rename|save|import|place)',re.I)


def invoke_tool(endpoint:str,tool_name:str,arguments:dict,*,confirmed:bool=False,allow_mutation:bool=False,timeout:int=20)->dict:
    _loopback(endpoint)
    if not confirmed:
        raise ValueError('Explicit --confirmed is required for every MCP tools/call')
    if not isinstance(arguments,dict):
        raise ValueError('MCP tool arguments must be a JSON object')
    if not isinstance(tool_name,str) or not tool_name or len(tool_name)>200:
        raise ValueError('Invalid MCP tool name')
    if _MUTATION.search(tool_name) and not allow_mutation:
        raise ValueError('Mutating or ambiguous MCP tool requires --allow-mutation')
    if timeout<1 or timeout>120:
        raise ValueError('Timeout must be between 1 and 120 seconds')
    listed=probe(endpoint,timeout=min(3,timeout))
    if listed.get('connection')!='connected':
        return {'result':'BLOCKED','reason':'No working MCP handshake','probe':listed}
    matches=[t for t in listed.get('discovered_tools',[]) if t.get('name')==tool_name]
    if len(matches)!=1:
        raise ValueError('Tool not advertised by the connected MCP server')
    schema=matches[0].get('inputSchema') or {'type':'object'}
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        raise ValueError('Install optional dependency jsonschema to validate discovered tool input')
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(arguments)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            raise ValueError('Redirect refused')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    session=None
    def request(method,params,reqid=None):
        nonlocal session
        message={'jsonrpc':'2.0','method':method}
        if reqid is not None: message['id']=reqid
        if params is not None: message['params']=params
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':PROTOCOL}
        if session:headers['Mcp-Session-Id']=session
        req=urllib.request.Request(endpoint,data=json.dumps(message).encode('utf-8'),headers=headers,method='POST')
        with opener.open(req,timeout=timeout) as response:
            session=response.headers.get('Mcp-Session-Id') or session
            raw=response.read(4_000_000)
            if reqid is None:return None
            result=_unpack(raw,response.headers.get('Content-Type','application/json'))
            if result.get('id')!=reqid:raise ValueError('MCP response ID mismatch')
            return result
    try:
        initialization=request('initialize',{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'verseforge-client','version':'0.9.0-rc1'}},101)
        if 'error' in initialization:
            return {'result':'BLOCKED','reason':'Initialization rejected','detail':initialization['error']}
        request('notifications/initialized',None)
        reply=request('tools/call',{'name':tool_name,'arguments':arguments},102)
        return {'result':'MCP_TOOL_RESPONSE','server':listed.get('server_identity'),'tool':tool_name,'response':reply,
                'uefn_compilation':'NOT VERIFIED BY THIS CLIENT','gameplay':'NOT TESTED',
                'warning':'Inspect tool response and independent UEFN evidence; tool output is untrusted data'}
    except urllib.error.HTTPError as e:
        return {'result':'BLOCKED','reason':'MCP HTTP error','http_status':e.code}
    except urllib.error.URLError as e:
        return {'result':'BLOCKED','reason':'MCP connection failure','detail':str(e)[:240]}
