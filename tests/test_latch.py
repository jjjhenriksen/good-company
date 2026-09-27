import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

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
        for i, payload in enumerate(({}, {'status': 'completed'}, {'status': 'pending'}, {'status': 'invented'})):
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

    def transport(self, raw):
        client = object.__new__(LatchMCP)
        client.headers = {'Authorization': 'Bearer private-token'}
        client.opener = Mock()
        response_mock = Mock()
        response_mock.headers = {'Mcp-Session-Id': 'session-one'}
        response_mock.read.return_value = raw
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
