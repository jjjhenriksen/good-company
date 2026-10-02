import base64
from email.message import EmailMessage
from pathlib import Path
import re
import unittest

from good_company.gmail_connector import GmailConnectorJournal, GmailConnectorReplies
from good_company.intake import dispatch
from good_company.providers import ProviderError
import test_tasks as fixtures
from test_core import NOW


class GmailConnectorTests(unittest.TestCase):
    def setUp(self):
        fixtures.TaskTests.setUp(self)
        self.calls, self.code = [], None
        self.owner = self.c.autonomy()['sender']
        self.profile = {'id': 'real-host-fixture-profile', 'email': self.owner}
        self.uid = 'a123'
        self.j = GmailConnectorJournal(Path(self.tmp.name) / 'connector.sqlite', self.call)
        self.p = GmailConnectorReplies(self.j, self.owner, {'unused': 'unused'}, 'fixture',
            coordinator=self.c, send_authority='fictional owner', unattended=True, clock=lambda: NOW)

    def tearDown(self):
        self.j.close()
        fixtures.TaskTests.tearDown(self)

    def call(self, name, args):
        self.calls.append((name, args))
        if name == 'gmail_get_profile':
            data = self.profile
        elif name == 'gmail_send_email':
            self.code = re.search(r'GCVERIFY ([0-9a-f]{64})', args['payload']['body']['content'])[1]
            data = {'id': self.uid, 'thread_id': self.uid, 'label_ids': ['SENT']}
        else:
            data = self.raw
        return {'isError': False, 'structuredContent': data}

    def reply(self, sender='alex@example.invalid', code=None, mid='b123'):
        mail = EmailMessage()
        mail['From'] = sender
        mail.set_content('\r\n> GCVERIFY ' + (code or self.code) + '\r\n')
        self.raw = {'id': mid, 'label_ids': ['INBOX'],
                    'raw': base64.urlsafe_b64encode(mail.as_bytes()).decode().rstrip('=')}

    def issue(self):
        return self.p.issue('alex@example.invalid', 'STOP', 'fixture-one', 'fictional owner request')

    def test_real_host_contract_and_shared_dispatcher(self):
        self.assertEqual(self.issue()['status'], 'active')
        self.reply()
        self.assertEqual(dispatch(self.c, self.p, 'b123', now=NOW)['action'], 'stop')
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
        self.assertEqual(len([n for n, _ in self.calls if n == 'gmail_read_email']), 2)
        send = next(a for n, a in self.calls if n == 'gmail_send_email')
        self.assertEqual(send['payload']['mime_type'], 'text/plain')
        self.assertEqual(send['to'], 'alex@example.invalid')

    def test_connector_profile_mismatch_does_not_send(self):
        self.profile['email'] = 'other@example.invalid'
        with self.assertRaisesRegex(ProviderError, 'account_mismatch'):
            self.issue()
        self.assertEqual([n for n, _ in self.calls], ['gmail_get_profile'])

    def test_other_sender_cannot_use_delivered_code(self):
        self.issue(); self.reply('sam@example.invalid')
        with self.assertRaisesRegex(ProviderError, 'proof_missing'):
            dispatch(self.c, self.p, 'b123', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))

    def test_raw_message_is_never_reconstructed_from_snippet_or_display_fields(self):
        self.issue(); self.reply()
        self.raw.pop('raw')
        self.raw.update(snippet='GCVERIFY ' + self.code, from_='alex@example.invalid')
        with self.assertRaises(ProviderError):
            dispatch(self.c, self.p, 'b123', now=NOW)

    def test_missing_receipt_stays_unknown_and_never_resends(self):
        self.uid = None
        self.assertEqual(self.issue()['status'], 'unknown')
        self.assertEqual(self.issue()['status'], 'unknown')
        self.assertEqual(self.p.reconcile_challenge('fixture-one')['status'], 'unknown')
        self.assertEqual(len([n for n, _ in self.calls if n == 'gmail_send_email']), 1)
        self.reply()
        with self.assertRaisesRegex(ProviderError, 'proof_missing'):
            dispatch(self.c, self.p, 'b123', now=NOW)

    def test_accepted_send_and_used_code_survive_reopening_journal(self):
        self.issue()
        self.j.close()
        self.j = GmailConnectorJournal(Path(self.tmp.name) / 'connector.sqlite', self.call)
        self.p = GmailConnectorReplies(self.j, self.owner, {'unused': 'unused'}, 'fixture',
            coordinator=self.c, send_authority='fictional owner', unattended=True, clock=lambda: NOW)
        self.assertEqual(self.p.reconcile_challenge('fixture-one')['status'], 'active')
        self.reply(); dispatch(self.c, self.p, 'b123', now=NOW)
        self.reply(mid='c123')
        with self.assertRaisesRegex(ProviderError, 'used'):
            dispatch(self.c, self.p, 'c123', now=NOW)
        self.assertEqual(len([n for n, _ in self.calls if n == 'gmail_send_email']), 1)

    def test_unstructured_error_and_unrelated_tools_are_rejected(self):
        self.j.call = lambda name, args: {'content': [{'type': 'text', 'text': 'private data'}]}
        with self.assertRaisesRegex(ProviderError, 'call_unconfirmed'):
            self.p.account()
        with self.assertRaisesRegex(ProviderError, 'outside_scope'):
            self.j.invoke('gmail_delete_emails', {})
        with self.assertRaisesRegex(ProviderError, 'calendar_unsupported'):
            self.p.calendar_page('unused', NOW, NOW)
