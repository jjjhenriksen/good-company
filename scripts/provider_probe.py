#!/usr/bin/env python3
"""Read-only Plow connected-tool discovery; never sends mail or prints credentials."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


def probe():
    base, token = os.environ.get('PLOW_API_BASE'), os.environ.get('PLOW_AGENT_TOKEN')
    if not base or not token:
        return {'ready': False, 'reason': 'missing_plow_connection_environment'}
    if urllib.parse.urlparse(base).scheme != 'https':
        return {'ready': False, 'reason': 'https_required'}
    headers = {'Authorization': 'Bearer ' + token}
    try:
        request = urllib.request.Request(base.rstrip('/') + '/v1/agents/me', headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            identity = json.load(response)
        url = identity.get('mcp_url')
        if not url or urllib.parse.urlparse(url).scheme != 'https':
            return {'ready': False, 'reason': 'connected_tool_endpoint_unavailable'}
        headers.update({'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})

        def call(method, params, request_id):
            data = json.dumps({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}).encode()
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=20) as response:
                session = response.headers.get('Mcp-Session-Id')
                if session:
                    headers['Mcp-Session-Id'] = session
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError('tool_catalog_too_large')
            text = raw.decode()
            if text.startswith(('event:', 'data:')):
                text = next(line[5:].strip() for line in text.splitlines() if line.startswith('data:'))
            result = json.loads(text)
            if result.get('error'):
                raise ValueError('mcp_request_refused')
            return result['result']

        call('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                           'clientInfo': {'name': 'good-company-provider-probe', 'version': '0.1'}}, 1)
        catalog = call('tools/list', {}, 2)
        return {'ready': False, 'discovery': 'reachable', 'tool_names': [tool['name'] for tool in catalog.get('tools', [])],
                'next': 'Verify exact calendar/mail schemas, account identity and permissions before implementing the adapter. Discovery alone does not establish readiness.'}
    except urllib.error.HTTPError as error:
        return {'ready': False, 'reason': 'connected_tool_http_error', 'http_status': error.code}
    except (OSError, ValueError, KeyError, StopIteration):
        return {'ready': False, 'reason': 'connected_tool_discovery_failed'}


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
