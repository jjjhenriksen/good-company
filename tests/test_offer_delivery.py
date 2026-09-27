"""Fictional offer delivery proof; no real mailbox or verified sender implied."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import unittest

from test_core import NOW, snapshot
import test_tasks as task_fixtures
import test_signups as signup_fixtures
from test_providers import FixtureProvider
from good_company.cycle import run_cycle
from good_company.onboarding import SetupCoordinator
from good_company.signups import apply
from good_company.providers import SendResult
from good_company.core import stamp
from good_company.tasks import WorkCoordinator


class OfferDeliveryTests(unittest.TestCase):
    tearDown = task_fixtures.TaskTests.tearDown
    reply = signup_fixtures.SignupTests.reply

    def setUp(self):
        task_fixtures.TaskTests.setUp(self)
        self.c.db.close()
        self.c = SetupCoordinator(Path(self.tmp.name) / 'tasks.sqlite')
        self.c.close_task('chairs', 'cancelled', 'fixture', now=NOW)
        self.c.add_shift({'id': 'packing', 'title': 'Packing shift', 'capacity': 1,
                          'slots': [task_fixtures.task('one')], 'signup_required': True}, 'fixture', now=NOW)
        self.p = FixtureProvider()

    def respond(self, person, action, message):
        return apply(self.c, self.reply(person, action, message), message, now=NOW)

    def cycle(self, name='offer-tick'):
        window = snapshot()
        return run_cycle(self.c, self.p, name, window['window_start'], window['window_end'], now=NOW)

    def offer(self):
        self.respond('alex', 'signup', 'signup')
        self.c.delegate(now=NOW)
        notice, = self.c.task_queue()
        return notice

    def test_cycle_sends_reserved_offer_once_without_confirming_attendance(self):
        self.respond('alex', 'signup', 'signup')
        result = self.cycle()
        self.assertEqual(result['sent'], 1)
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)
        notice, = self.c.task_queue()
        self.assertEqual(notice['kind'], 'offer')
        self.assertEqual(notice['status'], 'sent')
        self.assertEqual(notice['message']['to'], ['alex@example.invalid'])
        self.assertIn('Reply to accept or decline', notice['message']['body'])
        self.assertNotIn('within the work you agreed', notice['message']['body'])
        self.assertEqual(self.cycle('repeat-offer-tick')['sent'], 0)
        self.assertEqual(len(self.p.sent), 1)

    def test_acceptance_cancels_unsent_offer_and_queues_separate_assignment(self):
        notice = self.offer()
        self.respond('alex', 'accept_offer', 'accept')
        self.assertEqual(self.c.task_queue()[0]['status'], 'cancelled')
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
        self.c.delegate(now=NOW)
        self.assertEqual(self.c.shift_status('packing')['filled'], 1)
        pending = [n for n in self.c.task_queue() if n['status'] == 'pending']
        self.assertEqual({n['kind'] for n in pending}, {'assignment', '24h', '2h'})
        self.assertEqual(self.cycle()['sent'], 1)
        self.assertTrue(self.p.sent[0][0]['subject'].startswith('Your '))

    def test_decline_sends_only_the_waitlisted_replacements_offer(self):
        original = self.offer()
        self.respond('sam', 'signup', 'waiting')
        self.respond('alex', 'decline_offer', 'decline')
        self.assertEqual(self.cycle()['sent'], 1)
        self.assertEqual([s[0]['to'] for s in self.p.sent], [['sam@example.invalid']])
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == original['id'])['status'], 'cancelled')
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        self.assertEqual(self.cycle('repeat')['sent'], 0)

    def test_uncertain_offer_reconciles_after_acceptance_without_resending(self):
        self.respond('alex', 'signup', 'signup')
        self.p.result = TimeoutError('fictional ambiguous send')
        self.assertEqual(self.cycle()['uncertain'], 1)
        self.respond('alex', 'accept_offer', 'accept')
        self.p.result = SendResult('accepted', 'fixture-offer-receipt')
        self.assertEqual(self.cycle('reconcile')['reconciled'], 1)
        offer = next(n for n in self.c.task_queue() if n['kind'] == 'offer')
        self.assertEqual(offer['receipt'], 'fixture-offer-receipt')
        self.assertEqual(sum(' offer:' in s[0]['subject'] for s in self.p.sent), 1)

    def test_offer_claim_honors_pause_consent_and_changed_eligibility(self):
        notice = self.offer()
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'fixture pause', now=NOW)
        with self.assertRaisesRegex(ValueError, 'paused'):
            self.c.task_claim(notice['id'], now=NOW)
        policy['enabled'] = True
        self.c.configure_autonomy(policy, 'fixture resume', now=NOW)
        self.c.set_contact_consent('alex@example.invalid', False, 'verified fixture STOP', now=NOW)
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
        self.c.set_contact_consent('alex@example.invalid', True, 'verified fixture opt-in', now=NOW)
        person = task_fixtures.volunteer()
        person['availability'] = []
        self.c.set_volunteer(person, 'changed fixture availability', now=NOW)
        result = self.c.delegate(now=NOW)
        self.assertEqual(len(result['exceptions']), 1)
        self.assertTrue(all(n['status'] == 'cancelled' for n in self.c.task_queue()))
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(self.p.sent, [])

    def test_offer_uses_quiet_hours_and_shared_daily_budget(self):
        notice = self.offer()
        with self.assertRaisesRegex(ValueError, 'Quiet hours'):
            self.c.task_claim(notice['id'], now='2026-09-26T05:00:00Z')
        policy = self.c.autonomy()
        policy['max_reminders_per_day'] = 1
        self.c.configure_autonomy(policy, 'fixture shared budget', now=NOW)
        self.c.delegate(now=NOW)
        with self.c.db:
            self.c.log('send_claim', 'other-event', {}, stamp(NOW))
        with self.assertRaisesRegex(ValueError, 'shared daily'):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(self.c.task_queue()[0]['status'], 'pending')

    def test_cancelled_or_started_slot_cannot_send_its_offer(self):
        notice = self.offer()
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now='2026-09-27T17:00:00-07:00')
        self.c.close_task('packing:one', 'cancelled', 'fixture cancellation', now=NOW)
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(self.cycle()['sent'], 0)

    def test_changed_sender_refreshes_only_unattempted_offer(self):
        notice = self.offer()
        policy = self.c.autonomy()
        policy['sender'] = 'changed@example.invalid'
        self.c.configure_autonomy(policy, 'fixture sender change', now=NOW)
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
        self.c.delegate(now=NOW)
        result = self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(result['message']['sender'], policy['sender'])

    def test_concurrent_offer_claims_allow_one_attempt_and_restart_preserves_it(self):
        notice = self.offer()
        path = Path(self.tmp.name) / 'tasks.sqlite'
        def claim(_):
            c = WorkCoordinator(path)
            try:
                c.task_claim(notice['id'], now=NOW)
                return True
            except ValueError:
                return False
            finally:
                c.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(claim, range(2))), 1)
        self.c.db.close()
        self.c = SetupCoordinator(path)
        self.c.delegate(now=NOW)
        self.assertEqual(self.c.task_queue()[0]['status'], 'sending')
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
