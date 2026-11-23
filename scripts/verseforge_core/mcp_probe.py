"""Opt-in, read-only MCP capabilities handshake over loopback HTTP.
No write-tool invocation and no assumption that an MCP server is UEFN.
"""
from __future__ import annotations
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROTOCOL='2025-06-18'

def _loopback(url:str):
    p=urllib.parse.urlparse(url)
    if p.scheme!='http' or p.hostname not in ('localhost','127.0.0.1','::1') or p.username or p.password or p.path not in ('/mcp','/mcp/') or p.query or p.fragment:
        raise ValueError('MCP probe is restricted to explicitly provided loopback /mcp HTTP endpoints')
    return p


def _unpack(raw:bytes,content_type:str)->dict:
    body=raw.decode('utf-8','replace')
    if 'text/event-stream' in content_type:
        events=[]
        for line in body.splitlines():
            if line.startswith('data: '):
                try:events.append(json.loads(line[6:]))
                except ValueError:continue
        if not events:raise ValueError('No MCP JSON-RPC messages in SSE response')
        return events[-1]
    return json.loads(body)


def probe(endpoint:str,timeout=2)->dict:
    _loopback(endpoint)
    base={'endpoint':endpoint,'connection':'unconfigured','server_identity':'unverified',
          'read_only':True,'tool_names':[],'uefn_editor':'NOT TESTED','compile':'NOT TESTED'}
    class RejectRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            raise ValueError('MCP endpoint redirect refused')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),RejectRedirect())
    def rpc(method,params,rid,session=None):
        request={'jsonrpc':'2.0','id':rid,'method':method,'params':params}
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',
                 'MCP-Protocol-Version':PROTOCOL}
        if session:headers['Mcp-Session-Id']=session
        req=urllib.request.Request(endpoint,data=json.dumps(request).encode(),headers=headers,method='POST')
        with opener.open(req,timeout=timeout) as response:
            return _unpack(response.read(524288),response.headers.get('Content-Type','application/json')),response.headers.get('Mcp-Session-Id')
    try:
        init,session=rpc('initialize',{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'verseforge-probe','version':'0.9.0-rc1'}},1)
        if 'error' in init:
            return {**base,'connection':'protocol-error','detail':str(init['error'])[:300]}
        server=init.get('result',{}).get('serverInfo',{})
        base['server_identity']=server.get('name','unknown')
        # Notification required by MCP protocol. No tool is invoked.
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':PROTOCOL}
        if session:headers['Mcp-Session-Id']=session
        notification=urllib.request.Request(endpoint,data=json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'}).encode(),headers=headers,method='POST')
        try:
            with opener.open(notification,timeout=timeout):pass
        except urllib.error.HTTPError as e:
            if e.code not in (202,204):raise
        tools=[];cursor=None;seen=set()
        for page in range(10):
            params={'cursor':cursor} if cursor else {}
            response,_=rpc('tools/list',params,2+page,session)
            if 'error' in response:
                return {**base,'connection':'permission-or-protocol-error','detail':str(response['error'])[:300]}
            data=response.get('result',{})
            tools.extend(data.get('tools',[]))
            cursor=data.get('nextCursor')
            if not cursor:break
            if cursor in seen:raise ValueError('Repeated MCP tools cursor')
            seen.add(cursor)
        names=[x.get('name','') for x in tools if isinstance(x,dict)]
        schemata=[{'name':x.get('name'), 'inputSchema':x.get('inputSchema',{}),
                  'description':str(x.get('description',''))[:300]} for x in tools if isinstance(x,dict)]
        return {**base,'connection':'connected','protocol_version':init.get('result',{}).get('protocolVersion'),
                'tool_names':names,'tools_count':len(names),'discovered_tools':schemata,
                'capabilities':'DISCOVERED (not exercised)',
                'editor_identity':'UNKNOWN: no tool invoked to identify UEFN'}
    except urllib.error.HTTPError as e:
        return {**base,'connection':'permission-denied' if e.code in (401,403) else 'http-error',
                'http_status':e.code}
    except (urllib.error.URLError,TimeoutError,socket.timeout,ConnectionError) as e:
        return {**base,'connection':'inaccessible','detail':str(e)[:240]}
    except (ValueError,json.JSONDecodeError,TypeError) as e:
        return {**base,'connection':'protocol-error','detail':str(e)[:240]}


def inspect_config(path:Path)->dict:
    """Never guess a configured URL; extract explicit HTTP loopback MCP entries only."""
    if not path.is_file():return {'state':'not-configured','path':str(path)}
    try: data=json.loads(path.read_text(encoding='utf-8'))
    except ValueError:return {'state':'unreadable-config','path':str(path)}
    servers=data.get('mcpServers',{})
    if not isinstance(servers,dict):return {'state':'unsupported-format','path':str(path)}
    observed=[]
    for name,cfg in servers.items():
        if not isinstance(cfg,dict):continue
        url=cfg.get('url')
        if isinstance(url,str):
            try:_loopback(url)
            except ValueError:continue
            observed.append({'name':name,'url':url})
    return {'state':'configured' if observed else 'no-local-http-mcp','servers':observed,'path':str(path)}
