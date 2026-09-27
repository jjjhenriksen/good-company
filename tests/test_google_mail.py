import json
from pathlib import Path
import tempfile
import unittest

from good_company.google_mail import GoogleProvider
from good_company.latch import LatchOperations
from good_company.providers import ProviderError
from good_company.providers import Delivery
import test_tasks as task_fixtures
from test_core import NOW


class GoogleMailTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'private.sqlite'
        self.calls, self.results = [], []
        self.ops = LatchOperations(self.path, self.call)
        self.p = self.provider()
        self.msg = {'sender': 'sender@example.invalid', 'to': ['one@example.invalid'], 'bcc': [],
                    'subject': 'Fictional notice', 'body': 'Fictional task'}

    def tearDown(self):
        self.ops.close()
        self.tmp.cleanup()

    def provider(self, authority='fixture-owner', unattended=False):
        return GoogleProvider(self.ops, 'sender@example.invalid', {'scope': 'cal'}, 'cycle',
                              send_authority=authority, unattended=unattended)

    def call(self, tool, arguments):
        self.calls.append((tool, arguments))
        value = self.results.pop(0)
        if isinstance(value, Exception):
            raise value
        return {'structuredContent': value}

    def receipt(self, uid='a123'):
        return {'status': 'completed', 'exit_code': 0,
                'output': json.dumps({'messageId': uid, 'threadId': uid, 'from': 'access-token-user'})}

    def test_send_and_restart_reconcile_never_redispatch(self):
        self.results = [self.receipt()]
        self.assertEqual(self.p.send(self.msg, 'task:one').reference, 'gmail:a123')
        self.ops.close()
        self.ops = LatchOperations(self.path, self.call)
        self.p = self.provider()
        self.assertEqual(self.p.reconcile('task:one').outcome, 'accepted')
        self.assertEqual(self.p.send(self.msg, 'task:one').outcome, 'accepted')
        self.assertEqual(len(self.calls), 1)

    def test_pending_send_reconciles_genuine_receipt(self):
        self.results = [{'status': 'pending', 'handle': 'one'},
                        {'status': 'ready', 'result': self.receipt()}]
        self.assertEqual(self.p.send(self.msg, 'task:one').outcome, 'unknown')
        self.assertEqual(self.p.reconcile('task:one').outcome, 'accepted')
        self.assertEqual([c[0] for c in self.calls], ['plow_run_command', 'plow_get_result'])

    def test_timeout_and_nonzero_exit_do_not_imply_not_sent(self):
        for i, result in enumerate((TimeoutError(), {'status': 'completed', 'exit_code': 1, 'output': 'private failure'})):
            self.results = [result]
            self.assertEqual(self.p.send(self.msg, str(i)).outcome, 'unknown')
            self.assertEqual(self.p.reconcile(str(i)).outcome, 'unknown')
        self.assertEqual(len(self.calls), 2)

    def test_bcc_only_individual_copies_hide_other_recipients(self):
        self.msg.update(to=[], bcc=['one@example.invalid', 'two@example.invalid'])
        self.results = [self.receipt('a1'), self.receipt('a2')]
        self.assertEqual(self.p.send(self.msg, 'group').reference, 'gmail:a1,a2')
        first, second = [c[1]['argv'] for c in self.calls]
        self.assertIn('--to=one@example.invalid', first)
        self.assertFalse(any('two@example.invalid' in arg for arg in first))
        self.assertIn('--to=two@example.invalid', second)
        self.assertFalse(any('one@example.invalid' in arg for arg in second))

    def test_partial_group_remains_unknown_without_resend(self):
        self.msg.update(to=[], bcc=['one@example.invalid', 'two@example.invalid', 'three@example.invalid'])
        self.results = [self.receipt(), {'status': 'denied', 'reason': 'outside owner remit'}]
        self.assertEqual(self.p.send(self.msg, 'group').outcome, 'unknown')
        self.assertEqual(self.p.reconcile('group').outcome, 'unknown')
        self.assertEqual(self.p.send(self.msg, 'group').outcome, 'unknown')
        self.assertEqual(len(self.calls), 2)

    def test_single_denial_is_failed_and_never_retried(self):
        self.results = [{'status': 'denied'}]
        self.assertEqual(self.p.send(self.msg, 'one').outcome, 'failed')
        self.p.reconcile('one')
        self.assertEqual(len(self.calls), 1)

    def test_changed_payload_or_sender_rejected_before_dispatch(self):
        self.results = [self.receipt()]
        self.p.send(self.msg, 'one')
        self.msg['body'] = 'Different message'
        with self.assertRaises(ProviderError):
            self.p.send(self.msg, 'one')
        self.msg['sender'] = 'different@example.invalid'
        with self.assertRaises(ProviderError):
            self.p.send(self.msg, 'two')
        self.assertEqual(len(self.calls), 1)

    def test_no_authority_or_unsupported_idempotency_never_sends(self):
        with self.assertRaises(ProviderError):
            self.provider(None).send(self.msg, 'one')
        with self.assertRaises(ProviderError):
            self.p.send(self.msg, 'one', 'key')
        self.assertEqual(self.calls, [])

    def test_success_without_receipt_or_duplicate_receipts_is_unknown(self):
        self.results = [{'status': 'completed', 'exit_code': 0, 'output': '{}'}]
        self.assertEqual(self.p.send(self.msg, 'one').outcome, 'unknown')
        self.msg.update(to=[], bcc=['one@example.invalid', 'two@example.invalid'])
        self.results = [self.receipt(), self.receipt()]
        self.assertEqual(self.p.send(self.msg, 'group').outcome, 'unknown')

    def test_flag_like_body_is_literal_and_headers_reject_injection(self):
        self.msg['body'] = '--attach=/private/document'
        self.results = [self.receipt()]
        self.p.send(self.msg, 'one')
        self.assertIn('--body=--attach=/private/document', self.calls[0][1]['argv'])
        self.msg['subject'] = 'Subject\r\nBcc: other@example.invalid'
        with self.assertRaises(ProviderError):
            self.p.send(self.msg, 'two')

    def test_account_identity_does_not_imply_unattended_permission(self):
        self.results = [{'status': 'completed', 'accounts': [{'account': self.msg['sender']}], 'degraded': []}]
        self.assertFalse(self.p.account().unattended_send)
        self.assertTrue(self.provider(unattended=True).account().unattended_send)


class GoogleDeliveryTests(unittest.TestCase):
    setUp = task_fixtures.TaskTests.setUp
    tearDown = task_fixtures.TaskTests.tearDown

    def test_core_claim_and_late_receipt_use_one_remote_dispatch(self):
        self.c.delegate(now=NOW)
        notice = next(x for x in self.c.task_queue() if x['kind'] == 'assignment')
        sender = self.c.autonomy()['sender']
        calls = []

        def call(tool, arguments):
            calls.append((tool, arguments))
            if tool == 'plow_get_result':
                value = {'status': 'ready', 'result': {'status': 'completed', 'exit_code': 0,
                    'output': json.dumps({'messageId': 'a123', 'threadId': 'a123'})}}
            elif arguments['argv'] == ['plow-gog', 'accounts']:
                value = {'status': 'completed', 'accounts': [{'account': sender}], 'degraded': []}
            else:
                value = {'status': 'pending', 'handle': 'mail-job'}
            return {'structuredContent': value}

        ops = LatchOperations(Path(self.tmp.name) / 'mail.sqlite', call)
        try:
            provider = GoogleProvider(ops, sender, {'demo-events-only': 'cal'}, 'fixture',
                                      send_authority='fixture-owner', unattended=True)
            delivery = Delivery(self.c, provider)
            self.assertEqual(delivery.send('task', notice['id'], now=NOW)['status'], 'uncertain')
            with self.assertRaises(ValueError):
                delivery.send('task', notice['id'], now=NOW)
            self.assertEqual(delivery.reconcile('task', notice['id'], now=NOW)['status'], 'sent')
            sends = [c for c in calls if c[0] == 'plow_run_command' and c[1]['argv'][1:3] == ['gmail', 'send']]
            self.assertEqual(len(sends), 1)
        finally:
            ops.close()
