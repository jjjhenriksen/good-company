import unittest
from unittest.mock import patch
from dataclasses import replace
import test_tasks as base
from test_core import NOW
from test_providers import FixtureProvider
from good_company.replies import VerifiedReply, apply_verified_reply
from good_company.providers import ProviderError


class ReplyProvider(FixtureProvider):
    def verified_reply(self, message_id):
        return self.reply


class ReplyTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def provider(self, sender='alex@example.invalid', action='decline'):
        assignment = self.c.delegate(now=NOW)['assigned'][0]['assignment_id']
        p = ReplyProvider()
        p.reply = VerifiedReply('fixture-message', sender, True, 'fixture-identity-proof', action, assignment)
        return p

    def test_verified_decline_reassigns_and_replay_is_refused(self):
        p = self.provider()
        apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'][0]['volunteer_id'], 'sam')
        with self.assertRaises(ProviderError):
            apply_verified_reply(self.c, p, 'fixture-message', now=NOW)

    def test_spoofed_identity_and_other_participant_cannot_mutate(self):
        p = self.provider('sam@example.invalid')
        for reply in [p.reply, replace(p.reply, sender='alex@example.invalid', authenticated=False)]:
            p.reply = reply
            with self.assertRaises(ProviderError):
                apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
        self.assertEqual(self.c.db.execute('SELECT status FROM assignments').fetchone()[0], 'assigned')

    def test_verified_completion_stops_pending_notices(self):
        p = self.provider(action='complete')
        apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
        self.assertEqual(self.c.db.execute("SELECT status FROM tasks WHERE id='chairs'").fetchone()[0], 'completed')
        self.assertTrue(all(n['status'] == 'cancelled' for n in self.c.task_queue()))

    def test_stop_cannot_enable_consent(self):
        p = self.provider(action='stop')
        apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
        self.assertTrue(self.c.contact_allowed('sam@example.invalid'))

    def test_unrelated_mailbox_cannot_read_or_apply_reply(self):
        p = self.provider()
        for action in ('decline', 'complete', 'stop', 'preferences'):
            with self.subTest(action=action):
                p.reply = replace(p.reply, action=action)
                p.identity = replace(p.identity, sender='other-owner@example.invalid')
                before = list(self.c.db.iterdump())
                with patch.object(p, 'verified_reply', side_effect=AssertionError('wrong mailbox read')):
                    with self.assertRaisesRegex(ProviderError, 'reply_account_outside_remit'):
                        apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
                self.assertEqual(list(self.c.db.iterdump()), before)

    def test_missing_remit_cannot_accept_reply(self):
        p = self.provider(action='stop')
        with self.c.db:
            self.c.db.execute("DELETE FROM settings WHERE key='autonomy'")
        with self.assertRaisesRegex(ProviderError, 'reply_account_outside_remit'):
            apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))

    def test_account_change_during_provider_read_cannot_mutate_state(self):
        p = self.provider(action='stop')
        def change_remit(message_id):
            policy = self.c.autonomy()
            policy['sender'] = 'new-owner@example.invalid'
            self.c.configure_autonomy(policy, 'fixture account change', now=NOW)
            return p.reply
        with patch.object(p, 'verified_reply', side_effect=change_remit):
            with self.assertRaisesRegex(ProviderError, 'reply_account_outside_remit'):
                apply_verified_reply(self.c, p, 'fixture-message', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))
        self.assertEqual(self.c.db.execute('SELECT count(*) FROM processed_replies').fetchone()[0], 0)

    def test_verified_stop_still_works_when_sending_is_paused(self):
        p = self.provider(action='stop')
        p.identity = replace(p.identity, sender=p.identity.sender.upper())
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'pause fixture', now=NOW)
        self.assertEqual(apply_verified_reply(self.c, p, 'fixture-message', now=NOW)['status'], 'applied')
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
