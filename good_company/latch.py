"""Durable Latch command execution through the owner's authenticated MCP boundary.

The journal is private application state. Never publish it: command results may
contain mail or calendar data. No retry here ever dispatches a command twice.
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
import urllib.parse
import urllib.request

from .providers import ProviderError


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LatchMCP:
    """One authenticated MCP session; credentials stay in memory only."""
    def __init__(self, base, token):
        self._https(base)
        if not isinstance(token, str) or not token.strip():
            raise ProviderError('missing_latch_credentials')
        self.opener = urllib.request.build_opener(_NoRedirect)
        self.headers = {'Authorization': 'Bearer ' + token}
        identity = self._request(base.rstrip('/') + '/v1/agents/me')
        self.url = identity.get('mcp_url')
        self._https(self.url)
        self.headers.update({'Content-Type': 'application/json',
                             'Accept': 'application/json, text/event-stream'})
        self.sequence = 0
        result = self._rpc('initialize', {'protocolVersion': '2024-11-05',
            'capabilities': {}, 'clientInfo': {'name': 'good-company', 'version': '0.1'}})
        self.headers['MCP-Protocol-Version'] = result['protocolVersion']
        self._rpc('notifications/initialized', {}, notification=True)

    @staticmethod
    def _https(url):
        if not isinstance(url, str):
            raise ProviderError('invalid_latch_endpoint')
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ProviderError('invalid_latch_endpoint')

    def _request(self, url, envelope=None, notification=False):
        request = urllib.request.Request(url, headers=self.headers,
            data=None if envelope is None else json.dumps(envelope).encode())
        try:
            with self.opener.open(request, timeout=45) as response:
                session = response.headers.get('Mcp-Session-Id')
                if session:
                    self.headers['Mcp-Session-Id'] = session
                raw = response.read(2_000_001)
            if notification:
                return {}
            if len(raw) > 2_000_000:
                raise ValueError('oversized response')
            text = raw.decode()
            if text.lstrip().startswith(('event:', 'data:', ':')):
                candidates = []
                for block in text.replace('\r\n', '\n').split('\n\n'):
                    data = '\n'.join(line[5:].lstrip() for line in block.splitlines() if line.startswith('data:'))
                    if data:
                        candidates.append(json.loads(data))
                result = next(item for item in candidates if item.get('id') == envelope.get('id'))
            else:
                result = json.loads(text)
            if not isinstance(result, dict):
                raise ValueError('invalid envelope')
            if envelope is not None and result.get('id') != envelope.get('id'):
                raise ValueError('mismatched response')
            return result
        except Exception:
            # Provider errors may contain tokens, URLs or private message text.
            raise ProviderError('latch_transport_unconfirmed') from None

    def _rpc(self, method, params, notification=False):
        self.sequence += 1
        envelope = {'jsonrpc': '2.0', 'method': method, 'params': params}
        if not notification:
            envelope['id'] = self.sequence
        response = self._request(self.url, envelope, notification)
        if notification:
            return {}
        if response.get('error') or 'result' not in response:
            raise ProviderError('latch_rpc_unconfirmed')
        return response['result']

    def __call__(self, name, arguments):
        return self._rpc('tools/call', {'name': name, 'arguments': arguments})


def unpack(response):
    """Accept the structured result or exactly one JSON text block."""
    if not isinstance(response, dict):
        raise ProviderError('latch_tool_unconfirmed')
    if isinstance(response.get('structuredContent'), dict):
        value = response['structuredContent']
    else:
        blocks = [item['text'] for item in response.get('content', [])
                  if item.get('type') == 'text']
        try:
            value = json.loads(blocks[0]) if len(blocks) == 1 else None
        except (ValueError, TypeError):
            value = None
    if not isinstance(value, dict):
        raise ProviderError('latch_result_unconfirmed')
    if response.get('isError') and value.get('status') not in ('denied', 'blocked'):
        raise ProviderError('latch_tool_unconfirmed')
    return value


class LatchOperations:
    """Persist dispatch intent before network IO and poll only the saved handle.

    A crash after dispatch but before saving a handle is deliberately uncertain.
    Resolving that case requires provider evidence; a timeout is never permission
    to send again. Separate processes serialize dispatch using SQLite uniqueness.
    """
    def __init__(self, database, call):
        self.call = call
        # Restrict new and legacy files before SQLite can persist private results.
        # Do not change the process umask or permissions of a shared parent folder.
        fd = os.open(database, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        self.db = sqlite3.connect(database, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS latch_operations(
            operation_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
            state TEXT NOT NULL, poll_tool TEXT, handle TEXT, result TEXT)''')
        self.db.commit()

    def close(self):
        self.db.close()

    def execute(self, operation_id, argv, goal):
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ProviderError('missing_operation_id')
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or '\x00' in x for x in argv):
            raise ProviderError('invalid_command_arguments')
        if not isinstance(goal, str) or not goal.strip():
            raise ProviderError('missing_command_goal')
        arguments = {'argv': argv, 'goal': goal, 'wait_ms': 1000}
        fingerprint = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
        with self.db:
            inserted = self.db.execute('INSERT OR IGNORE INTO latch_operations VALUES(?,?,?,NULL,NULL,NULL)',
                (operation_id, fingerprint, 'uncertain')).rowcount
        row = self.db.execute('SELECT * FROM latch_operations WHERE operation_id=?', (operation_id,)).fetchone()
        if row['fingerprint'] != fingerprint:
            raise ProviderError('operation_payload_changed')
        if not inserted:
            return self.status(operation_id)
        try:
            result = unpack(self.call('plow_run_command', arguments))
        except Exception:
            return self.status(operation_id)
        return self._save(operation_id, result, None)

    def status(self, operation_id):
        row = self.db.execute('SELECT * FROM latch_operations WHERE operation_id=?', (operation_id,)).fetchone()
        if not row:
            raise ProviderError('unknown_operation')
        return {'state': row['state'], 'handle': row['handle'],
                'result': json.loads(row['result']) if row['result'] else None}

    def poll(self, operation_id):
        row = self.db.execute('SELECT * FROM latch_operations WHERE operation_id=?', (operation_id,)).fetchone()
        if not row:
            raise ProviderError('unknown_operation')
        if row['state'] not in ('pending', 'running'):
            return self.status(operation_id)
        try:
            result = unpack(self.call(row['poll_tool'], {'handle': row['handle']}))
        except Exception:
            # An observation failure does not mean the underlying call stopped.
            return self.status(operation_id)
        return self._save(operation_id, result, row['result'])

    def _save(self, operation_id, result, previous):
        if result.get('status') == 'ready' and isinstance(result.get('result'), dict):
            result = result['result']
        result = dict(result, _received_at=datetime.now(timezone.utc).isoformat())
        state = result.get('status', 'uncertain')
        poll_tool, handle = None, None
        if state in ('pending', 'running'):
            handle = result.get('handle')
            if not isinstance(handle, str) or not handle:
                state, handle = 'uncertain', None
            else:
                poll_tool = 'plow_get_result' if state == 'pending' else 'plow_get_output'
        elif state == 'completed':
            if 'exit_code' in result and type(result['exit_code']) is not int:
                state = 'uncertain'
        elif state not in ('denied', 'blocked', 'failed', 'expired', 'unknown'):
            state = 'uncertain'
        with self.db:
            self.db.execute('UPDATE latch_operations SET state=?,poll_tool=?,handle=?,result=? WHERE operation_id=? AND result IS ?',
                (state, poll_tool, handle, json.dumps(result), operation_id, previous))
        return self.status(operation_id)
