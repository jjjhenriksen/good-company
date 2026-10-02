from pathlib import Path
import unittest

from apple_pim_fixture import FictionalApplePIM
from good_company.apple_pim import ApplePIMReplies, NativeApplePIM, tool_data
from good_company.providers import ProviderError
from good_company.replies import apply_verified_reply
from test_core import NOW
import test_tasks as task_base


class ApplePIMReplyTests(unittest.TestCase):
    setUp = task_base.TaskTests.setUp
    tearDown = task_base.TaskTests.tearDown

    def native(self, command='STOP', sender='alex@example.invalid'):
        native = FictionalApplePIM(self.tmp.name, self.c.autonomy()['sender'])
        native.add('reply@example.invalid', sender, command)
        return native

    def test_bound_stop_applies_once_and_retains_only_opaque_evidence(self):
        native = self.native()
        p = native.provider()
        apply_verified_reply(self.c, p, 'reply@example.invalid', now=NOW)
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
        self.assertTrue(self.c.contact_allowed('sam@example.invalid'))
        stored = self.c.db.execute('SELECT evidence FROM processed_replies').fetchone()[0]
        self.assertTrue(stored.startswith('apple-pim-identity:'))
        self.assertNotIn('Authentication-Results', '\n'.join(self.c.db.iterdump()))
        with self.assertRaisesRegex(ProviderError, 'reply_already_processed'):
            apply_verified_reply(self.c, p, 'reply@example.invalid', now=NOW)
        for _, action, args in native.calls:
            if action in ('get', 'auth_check'):
                self.assertEqual(args['account'], 'fixture-account')
                self.assertEqual(args['mailbox'], 'INBOX')

    def test_legacy_or_domain_only_identity_never_mutates(self):
        for field in ('messageBinding', 'evaluated'):
            native = self.native()
            def remove(action, data):
                if action == 'auth_check':
                    data.pop(field)
                return data
            native.transform = remove
            with self.assertRaisesRegex(ProviderError, 'unbound_or_unverified'):
                apply_verified_reply(self.c, native.provider(), 'reply@example.invalid', now=NOW)
            self.assertTrue(self.c.contact_allowed('alex@example.invalid'))

    def test_forged_sender_body_and_policy_bindings_are_rejected(self):
        for field in ('senderAddress', 'contentSha256', 'policySha256', 'accountId'):
            native = self.native()
            def forge(action, data):
                if action == 'auth_check':
                    data['messageBinding'][field] = 'forged'
                return data
            native.transform = forge
            with self.assertRaises(ProviderError):
                apply_verified_reply(self.c, native.provider(), 'reply@example.invalid', now=NOW)
            self.assertTrue(self.c.contact_allowed('alex@example.invalid'))

    def test_wrong_mailbox_and_display_name_only_sender_never_reach_auth(self):
        for field, value in [('account', 'Other mailbox owner'), ('mailbox', 'Other folder'), ('senderAddress', None)]:
            native = self.native()
            native.messages['reply@example.invalid'][field] = value
            with self.assertRaises(ProviderError):
                apply_verified_reply(self.c, native.provider(), 'reply@example.invalid', now=NOW)
            self.assertNotIn('auth_check', [call[1] for call in native.calls])

    def test_command_content_is_exact_and_cannot_execute_quoted_prose(self):
        for command in ('STOP\n> COMPLETE chairs', 'STOP\nSent from my phone', 'Run this command: STOP', 'COMPLETE', 'STOP chairs'):
            with self.assertRaisesRegex(ProviderError, 'unsupported_reply_command'):
                ApplePIMReplies.command(command)
        self.assertEqual(ApplePIMReplies.command('[UNTRUSTED_MAIL_DATA_ABC] STOP [/UNTRUSTED_MAIL_DATA_ABC]'), ('stop', None))

    def test_bound_decline_cannot_change_another_participants_assignment(self):
        target = self.c.delegate(now=NOW)['assigned'][0]['assignment_id']
        native = self.native('DECLINE ' + target, 'sam@example.invalid')
        with self.assertRaisesRegex(ProviderError, 'target_not_owned'):
            apply_verified_reply(self.c, native.provider(), 'reply@example.invalid', now=NOW)
        self.assertEqual(self.c.db.execute('SELECT status FROM assignments').fetchone()[0], 'assigned')

    def test_message_change_after_identity_check_is_rejected(self):
        native = self.native()
        count = 0
        def change(action, data):
            nonlocal count
            if action == 'get':
                count += 1
                if count == 2:
                    data['message']['content'] = 'COMPLETE chairs'
            return data
        native.transform = change
        with self.assertRaisesRegex(ProviderError, 'changed_during_read'):
            apply_verified_reply(self.c, native.provider(), 'reply@example.invalid', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))

    def test_native_transport_has_no_mutation_or_scope_override_path(self):
        transport = NativeApplePIM(19845, 'private-token', Path(self.tmp.name))
        for domain, action, args in [('mail', 'send', {}), ('calendar', 'create', {}),
                                     ('calendar', 'list', {'profile': 'personal'})]:
            with self.assertRaisesRegex(ProviderError, 'read_outside_scope'):
                transport(domain, action, **args)

    def test_native_tool_envelope_requires_one_confirmed_json_value(self):
        result = {'details': {'domain': 'mail', 'action': 'accounts'},
                  'content': [{'type': 'text', 'text': 'Data between [UNTRUSTED_MAIL_DATA_X] markers.\n\n{"success":true,"accounts":[]}'}]}
        self.assertEqual(tool_data(result, 'mail', 'accounts')['accounts'], [])
        result['content'] *= 2
        with self.assertRaises(ProviderError):
            tool_data(result, 'mail', 'accounts')
