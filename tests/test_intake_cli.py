import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from good_company import intake_cli
import test_tasks as fixtures
from test_core import NOW


class IntakeCLITests(unittest.TestCase):
    setUp = fixtures.TaskTests.setUp
    tearDown = fixtures.TaskTests.tearDown

    def run_cli(self, config, *arguments):
        path = Path(self.tmp.name) / 'intake.json'
        path.write_text(json.dumps(config))
        output = io.StringIO()
        with patch('sys.argv', ['good-company-intake', '--config', str(path), *arguments]), contextlib.redirect_stdout(output):
            code = intake_cli.main()
        return code, json.loads(output.getvalue())

    def config(self):
        return {'db': 'tasks.sqlite', 'journal': 'latch.sqlite', 'account': self.c.autonomy()['sender'],
                'scopes': {'demo-events-only': 'cal'}, 'send_authority': 'fictional owner', 'unattended': True}

    def test_paused_or_unattested_issuance_never_opens_a_provider(self):
        config = self.config(); config['unattended'] = False
        with patch.object(intake_cli, 'LatchMCP') as mcp:
            code, result = self.run_cli(config, 'issue', '--recipient', 'alex@example.invalid',
                '--command', 'STOP', '--operation-id', 'fixture', '--authority', 'fictional owner')
            self.assertEqual((code, result['reason']), (2, 'verification_send_outside_remit'))
            mcp.assert_not_called()
        policy = self.c.autonomy(); policy['enabled'] = False
        self.c.configure_autonomy(policy, 'fictional pause', now=NOW)
        config['unattended'] = True
        with patch.object(intake_cli, 'LatchMCP') as mcp:
            self.assertEqual(self.run_cli(config, 'issue', '--recipient', 'alex@example.invalid',
                '--command', 'STOP', '--operation-id', 'fixture', '--authority', 'fictional owner')[0], 2)
            mcp.assert_not_called()
        self.assertFalse((Path(self.tmp.name) / 'latch.sqlite').exists())

    def test_wrong_owner_or_shared_journal_is_rejected_before_connection(self):
        for changes in ({'account': 'other@example.invalid'}, {'journal': 'tasks.sqlite'}):
            with patch.object(intake_cli, 'LatchMCP') as mcp:
                code, _ = self.run_cli({**self.config(), **changes}, 'receive', '--message-id', 'abc123')
                self.assertEqual(code, 2)
                mcp.assert_not_called()

    def test_receive_routes_exact_id_when_sending_is_paused(self):
        policy = self.c.autonomy(); policy['enabled'] = False
        self.c.configure_autonomy(policy, 'fictional pause', now=NOW)
        config = self.config(); config.update(unattended=False, send_authority=None)
        with patch.object(intake_cli, 'LatchMCP'), patch.object(intake_cli, 'GoogleReplyProvider') as provider, \
                patch.object(intake_cli, 'dispatch', return_value={'status': 'applied', 'action': 'stop'}) as dispatch:
            code, result = self.run_cli(config, 'receive', '--message-id', 'abc123')
            self.assertEqual((code, result['action']), (0, 'stop'))
            self.assertEqual(dispatch.call_args.args[2], 'abc123')
            provider.return_value.issue.assert_not_called()
