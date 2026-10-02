from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from apple_pim_fixture import FictionalApplePIM
from good_company.intake import ApplePIMIntake, dispatch
from good_company.providers import ProviderError
from good_company.tasks import WorkCoordinator
from test_core import NOW
import test_shifts as shift_base
import test_signups as signup_base


class ProviderIntakeTests(unittest.TestCase):
    setUp = shift_base.ShiftTests.setUp
    tearDown = shift_base.ShiftTests.tearDown
    prepare = signup_base.SignupTests.prepare
    shift = shift_base.ShiftTests.shift

    def native(self, owner=None):
        return FictionalApplePIM(self.tmp.name, owner or self.c.autonomy()['sender'])

    def provider(self, native):
        return ApplePIMIntake(native, 'fixture-account', native.owner, 'INBOX', native.policy_path)

    def reply(self, native, mid, person, command):
        native.add(mid, person + '@example.invalid', command)
        return dispatch(self.c, self.provider(native), mid, now=NOW)

    def test_same_verified_path_handles_offer_accept_decline_and_waitlist(self):
        self.prepare()
        native = self.native()
        self.assertEqual(self.reply(native, 'one', 'alex', 'SIGNUP packing:one')['status'], 'offered')
        self.assertEqual(self.reply(native, 'two', 'sam', 'SIGNUP packing:one')['status'], 'waitlisted')
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        self.assertEqual(self.reply(native, 'three', 'alex', 'ACCEPT packing:one')['status'], 'confirmed')
        self.assertEqual(self.c.shift_status('packing')['filled'], 1)
        self.assertEqual(self.reply(native, 'four', 'alex', 'DECLINE-OFFER packing:one')['status'], 'declined')
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        self.assertEqual(self.c.db.execute("SELECT volunteer_id FROM assignments WHERE status='offered'").fetchone()[0], 'sam')

    def test_consumed_message_cannot_be_replayed_into_a_different_workflow(self):
        self.prepare()
        native = self.native()
        self.reply(native, 'same-message', 'alex', 'SIGNUP packing:one')
        native.add('same-message', 'alex@example.invalid', 'STOP')
        with self.assertRaisesRegex(ProviderError, 'intake_already_claimed'):
            dispatch(self.c, self.provider(native), 'same-message', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))
        self.assertEqual(self.c.db.execute('SELECT count(*) FROM inbound_intake').fetchone()[0], 1)

    def test_wrong_owner_mailbox_never_reads_participant_content(self):
        native = self.native('other@example.invalid')
        native.add('one', 'alex@example.invalid', 'STOP')
        with self.assertRaisesRegex(ProviderError, 'reply_account_outside_remit'):
            dispatch(self.c, self.provider(native), 'one', now=NOW)
        self.assertFalse(any(call[1] == 'get' for call in native.calls))

    def test_native_unbound_signup_cannot_reserve_capacity(self):
        self.prepare()
        native = self.native()
        native.add('one', 'alex@example.invalid', 'SIGNUP packing:one')
        def legacy(action, data):
            if action == 'auth_check':
                data.pop('messageBinding')
            return data
        native.transform = legacy
        with self.assertRaises(ProviderError):
            dispatch(self.c, self.provider(native), 'one', now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)

    def test_concurrent_duplicate_message_has_one_claim_and_one_mutation(self):
        self.prepare()
        native = self.native()
        native.add('one', 'alex@example.invalid', 'SIGNUP packing:one')
        def consume(_):
            c = WorkCoordinator(Path(self.tmp.name) / 'tasks.sqlite')
            try:
                return dispatch(c, self.provider(native), 'one', now=NOW)['status']
            except ProviderError:
                return 'replay-rejected'
            finally:
                c.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(consume, range(2)))
        self.assertCountEqual(result, ['offered', 'replay-rejected'])
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)

    def test_paused_stop_remains_available_but_signup_is_rejected(self):
        self.prepare()
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'Owner paused fictional test', now=NOW)
        native = self.native()
        self.assertEqual(self.reply(native, 'stop', 'alex', 'STOP')['status'], 'applied')
        with self.assertRaisesRegex(ProviderError, 'signup_account_outside_remit'):
            self.reply(native, 'signup', 'sam', 'SIGNUP packing:one')
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)

    def test_account_switch_during_verified_read_cannot_mutate(self):
        native = self.native()
        native.add('one', 'alex@example.invalid', 'STOP')
        p = self.provider(native)
        original = p.account()
        with patch.object(p, 'account', side_effect=[original, replace(original, account_id='different')]):
            with self.assertRaisesRegex(ProviderError, 'intake_account_changed'):
                dispatch(self.c, p, 'one', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))
