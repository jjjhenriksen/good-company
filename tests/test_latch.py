import json
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from good_company.latch import LatchMCP, LatchOperations, unpack
from good_company.providers import ProviderError


def response(value):
    return {'content': [{'type': 'text', 'text': json.dumps(value)}]}


class LatchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'private.sqlite'
        self.calls = []
        self.responses = []
        self.operations = LatchOperations(self.path, self.call)

    def tearDown(self):
        self.operations.close()
        self.directory.cleanup()

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return response(result)

    def execute(self, argv=None):
        return self.operations.execute('calendar:one', argv or ['plow-gog', 'calendar', '--help'], 'Inspect supported calendar flags')

    def test_journal_is_private_under_permissive_umask(self):
        path = Path(self.directory.name) / 'fresh.sqlite'
        previous_umask = os.umask(0o022)
        try:
            operations = LatchOperations(path, self.call)
        finally:
            os.umask(previous_umask)
        try:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        finally:
            operations.close()

    def test_reopen_tightens_legacy_journal_without_losing_receipts(self):
        self.responses = [{'status': 'completed', 'exit_code': 0, 'output': 'fictional private result'}]
        before = self.execute()
        self.operations.close()
        self.path.chmod(0o644)
        self.operations = LatchOperations(self.path, self.call)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.operations.status('calendar:one'), before)
        self.assertEqual(self.execute(), before)
        self.assertEqual(len(self.calls), 1)

    def test_restart_polls_saved_handle_without_dispatch(self):
        self.responses = [{'status': 'pending', 'handle': 'approval-one'},
                          {'status': 'ready', 'result': {'status': 'completed', 'exit_code': 0, 'output': '{}'}}]
        self.assertEqual(self.execute()['state'], 'pending')
        self.operations.close()
        self.operations = LatchOperations(self.path, self.call)
        self.assertEqual(self.execute()['state'], 'pending')
        self.assertEqual(self.operations.poll('calendar:one')['state'], 'completed')
        self.execute()
        self.assertEqual([x[0] for x in self.calls], ['plow_run_command', 'plow_get_result'])
        self.assertEqual(self.calls[1][1], {'handle': 'approval-one'})

    def test_observation_timeout_retains_live_handle(self):
        self.responses = [{'status': 'pending', 'handle': 'one'}, TimeoutError('private'),
                          {'status': 'ready', 'result': {'status': 'completed', 'exit_code': 0}}]
        self.execute()
        self.assertEqual(self.operations.poll('calendar:one')['handle'], 'one')
        self.assertEqual(self.operations.poll('calendar:one')['state'], 'completed')
        self.assertEqual(len([x for x in self.calls if x[0] == 'plow_run_command']), 1)

    def test_dispatch_timeout_is_uncertain_forever_without_receipt(self):
        self.responses = [TimeoutError('private credential')]
        self.assertEqual(self.execute()['state'], 'uncertain')
        self.execute()
        self.operations.poll('calendar:one')
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn('credential', self.path.read_bytes().decode(errors='ignore'))

    def test_changed_payload_cannot_reuse_operation(self):
        self.responses = [{'status': 'completed', 'exit_code': 0}]
        self.execute()
        with self.assertRaisesRegex(ProviderError, 'payload_changed'):
            self.execute(['plow-gog', 'gmail', 'send'])
        self.assertEqual(len(self.calls), 1)

    def test_two_workers_dispatch_once(self):
        self.responses = [{'status': 'pending', 'handle': 'one'}]
        second = LatchOperations(self.path, self.call)
        try:
            self.execute()
            second.execute('calendar:one', ['plow-gog', 'calendar', '--help'], 'Inspect supported calendar flags')
            self.assertEqual(len(self.calls), 1)
        finally:
            second.close()

    def test_pending_to_running_uses_correct_job_handle(self):
        self.responses = [{'status': 'pending', 'handle': 'rpc'},
                          {'status': 'ready', 'result': {'status': 'running', 'handle': 'job'}},
                          {'status': 'completed', 'exit_code': 0}]
        self.execute()
        self.operations.poll('calendar:one')
        self.operations.poll('calendar:one')
        self.assertEqual(self.calls[-1], ('plow_get_output', {'handle': 'job'}))

    def test_denials_and_expired_handles_never_redispatch(self):
        for state in ('denied', 'blocked', 'failed', 'expired', 'unknown'):
            with self.subTest(state=state):
                self.responses = [{'status': state}]
                self.operations.execute(state, ['plow-gog', '--help'], 'Read help')
                self.operations.execute(state, ['plow-gog', '--help'], 'Read help')
                self.operations.poll(state)
        self.assertEqual(len(self.calls), 5)

    def test_malformed_results_do_not_become_success(self):
        for i, payload in enumerate(({}, {'status': 'completed', 'exit_code': '0'}, {'status': 'pending'}, {'status': 'invented'})):
            self.responses = [payload]
            self.assertEqual(self.operations.execute(str(i), ['plow-gog', '--help'], 'Read help')['state'], 'uncertain')
        with self.assertRaises(ProviderError):
            unpack({'isError': True, 'structuredContent': {'status': 'completed'}})

    def test_late_poll_cannot_overwrite_completion(self):
        self.responses = [{'status': 'pending', 'handle': 'rpc'}]
        self.execute()
        old = self.operations.db.execute('SELECT result FROM latch_operations').fetchone()[0]
        self.operations._save('calendar:one', {'status': 'completed', 'exit_code': 0}, old)
        self.operations._save('calendar:one', {'status': 'pending', 'handle': 'rpc'}, old)
        self.assertEqual(self.operations.status('calendar:one')['state'], 'completed')

    def test_https_endpoints_only(self):
        for value in (None, 'http://localhost', 'https://user:secret@example.com', 'https://example.com/#secret'):
            with self.assertRaises(ProviderError):
                LatchMCP._https(value)
        LatchMCP._https('https://example.com/mcp')

    def test_error_envelope_preserves_gatekeeper_denial(self):
        payload = response({'status': 'denied', 'reason': 'outside owner instructions'})
        payload['isError'] = True
        self.operations.call = lambda *args: payload
        self.assertEqual(self.execute()['state'], 'denied')
        self.assertEqual(self.execute()['result']['reason'], 'outside owner instructions')

    def test_structured_accounts_completion_without_process_exit(self):
        self.responses = [{'status': 'completed', 'accounts': [], 'degraded': []}]
        self.assertEqual(self.execute()['state'], 'completed')

    def transport(self, raw):
        client = object.__new__(LatchMCP)
        client.headers = {'Authorization': 'Bearer private-token'}
        client.opener = Mock()
        response_mock = Mock()
        response_mock.headers = {'Mcp-Session-Id': 'session-one'}
        stream = io.BytesIO(raw)
        response_mock.read.side_effect = stream.read
        response_mock.read1.side_effect = stream.read1
        client.opener.open.return_value.__enter__ = Mock(return_value=response_mock)
        client.opener.open.return_value.__exit__ = Mock(return_value=False)
        return client

    def test_sse_uses_matching_response_after_notification(self):
        client = self.transport(b': keepalive\n\nevent: message\ndata: {"method":"notice"}\n\nevent: message\ndata: {"id":7,"result":{}}\n\n')
        self.assertEqual(client._request('https://example.com/mcp', {'id': 7})['id'], 7)
        self.assertEqual(client.headers['Mcp-Session-Id'], 'session-one')

    def test_mismatched_or_oversized_response_is_redacted(self):
        for raw in (b'{"id":8,"error":"private-token"}', b'x' * 2_000_001):
            with self.subTest(size=len(raw)):
                client = self.transport(raw)
                with self.assertRaisesRegex(ProviderError, '^latch_transport_unconfirmed$'):
                    client._request('https://example.com/mcp', {'id': 7})

    def test_sse_returns_matching_result_without_waiting_for_eof(self):
        client = self.transport(b'')
        response = client.opener.open.return_value.__enter__.return_value
        response.headers['Content-Type'] = 'text/event-stream'
        response.read1.side_effect = [
            b'data: {"method":"notification"}\n', b'\n',
            b'data: {"id":7,"result":{}}\n', b'\n',
            TimeoutError('stream remains open'),
        ]
        response.read.side_effect = TimeoutError('must not wait for EOF')
        self.assertEqual(client._request('https://example.com/mcp', {'id': 7}),
                         {'id': 7, 'result': {}})
        self.assertEqual(response.read1.call_count, 4)
        response.read.assert_not_called()

    def test_sse_missing_result_remains_unconfirmed(self):
        client = self.transport(b'data: {"id":8,"result":{}}\n\n')
        client.opener.open.return_value.__enter__.return_value.headers['Content-Type'] = 'text/event-stream'
        with self.assertRaisesRegex(ProviderError, '^latch_transport_unconfirmed$'):
            client._request('https://example.com/mcp', {'id': 7})

    def test_sse_multiline_data_and_crlf_are_supported(self):
        client = self.transport(b'data: {"id":7,\r\ndata: "result":{}}\r\n\r\n')
        client.opener.open.return_value.__enter__.return_value.headers['Content-Type'] = 'text/event-stream'
        self.assertEqual(client._request('https://example.com/mcp', {'id': 7})['id'], 7)

    def test_sse_total_byte_and_elapsed_budgets_remain_bounded(self):
        client = self.transport(b'data: ' + b'x' * 2_000_000)
        response = client.opener.open.return_value.__enter__.return_value
        response.headers['Content-Type'] = 'text/event-stream'
        with self.assertRaisesRegex(ProviderError, '^latch_transport_unconfirmed$'):
            client._request('https://example.com/mcp', {'id': 7})
        client = self.transport(b'data: unfinished')
        response = client.opener.open.return_value.__enter__.return_value
        response.headers['Content-Type'] = 'text/event-stream'
        with patch('good_company.latch.time.monotonic', side_effect=[0, 0, 46]):
            with self.assertRaisesRegex(ProviderError, '^latch_transport_unconfirmed$'):
                client._request('https://example.com/mcp', {'id': 7})
        self.assertEqual(response.read1.call_count, 1)

    def test_sse_fragmented_utf8_and_crlf_do_not_require_eof(self):
        client = self.transport(b'')
        response = client.opener.open.return_value.__enter__.return_value
        response.headers['Content-Type'] = 'text/event-stream'
        raw = 'data: {"id":7,"result":{"name":"José"}}\r\n\r\n'.encode()
        split = raw.index(b'\xc3') + 1
        response.read1.side_effect = [raw[:split], raw[split:-3], raw[-3:],
                                     TimeoutError('stream remains open')]
        self.assertEqual(client._request('https://example.com/mcp', {'id': 7})['result'],
                         {'name': 'José'})
        self.assertEqual(response.read1.call_count, 3)
