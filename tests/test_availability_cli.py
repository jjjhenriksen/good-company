from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from good_company.availability_cli import main
from good_company.providers import ProviderError


class AvailabilityCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = Path(self.tmp.name) / 'availability.json'
        self.data = {'journal': 'operations.sqlite', 'account': 'owner@example.invalid',
                     'scopes': {'personal-busy': 'personal@example.invalid'}}
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, name, arguments):
        argv = arguments['argv']
        self.calls.append(argv)
        if argv == ['plow-gog', 'accounts']:
            payload = {'status': 'completed', 'accounts': [{'account': self.data['account']}]}
        else:
            payload = {'status': 'completed', 'exit_code': 0,
                       'output': json.dumps({'calendars': {'personal@example.invalid': {}}})}
        return {'structuredContent': payload}

    def run_cli(self, scope='personal-busy', failure=None):
        self.config.write_text(json.dumps(self.data))
        output = StringIO()
        argv = ['good-company-availability', '--config', str(self.config), '--check-id', 'fictional-check',
                '--scope', scope, '--start', '2026-09-28T17:00:00Z', '--end', '2026-09-28T18:00:00Z']
        with patch('sys.argv', argv), redirect_stdout(output), \
                patch('good_company.availability_cli.LatchMCP', return_value=self.call, side_effect=failure) as transport:
            code = main()
        return code, json.loads(output.getvalue()), transport.call_count

    def test_read_only_command_uses_relative_private_journal_and_replays(self):
        code, result, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertTrue(result['available'])
        self.assertTrue((Path(self.tmp.name) / 'operations.sqlite').exists())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.run_cli()[1], result)
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn('personal@example.invalid', json.dumps(result))

    def test_unconfigured_scope_never_initializes_transport(self):
        code, result, calls = self.run_cli(scope='other')
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(calls, 0)

    def test_configuration_cannot_add_sender_authority_or_simulated_clock(self):
        for key, value in (('send_authority', 'not a sending command'), ('now', '2026-09-28T17:00:00Z')):
            self.data[key] = value
            code, result, calls = self.run_cli()
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'unavailable')
            self.assertEqual(calls, 0)
            del self.data[key]

    def test_transport_unavailability_never_becomes_free(self):
        code, result, _ = self.run_cli(failure=ProviderError('latch_transport_unconfirmed'))
        self.assertEqual(code, 2)
        self.assertNotIn('available', result)
        self.assertEqual(result['reason'], 'latch_transport_unconfirmed')
