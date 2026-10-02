from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from good_company.modules import ModuleCoordinator
from good_company.providers import Account, Delivery, SendResult
from module_fixture import NOW, booking, coordinator, policy, resource


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.sqlite'
        self.c = coordinator(self.path)
        self.c.add_resource(resource=resource(), actor='owner', authority='fictional custodian', now=NOW)

    def tearDown(self):
        self.c.db.close()
        self.tmp.cleanup()

    def book(self, value=None, actor='alex'):
        return self.c.book_resource(booking=value or booking(), actor=actor, authority='fictional verified request', now=NOW)

    def notice(self):
        return self.c.module_notice(module='resources', record_id='booking-one', recipient='alex@example.invalid',
                                    due=NOW.isoformat(), actor='alex', authority='fictional notice remit', now=NOW)['id']

    def test_booking_replay_release_and_capacity(self):
        result = self.book()
        self.assertTrue(result['receipt'].startswith('good-company-ledger:'))
        self.assertTrue(self.book()['replayed'])
        with self.assertRaisesRegex(ValueError, 'capacity'):
            self.book(booking('second', 'sam'), 'sam')
        self.c.cancel_booking('booking-one', 'alex', 'verified cancellation', now=NOW)
        self.assertEqual(self.book(booking('second', 'sam'), 'sam')['status'], 'booked')
        with self.assertRaises(ValueError):
            self.book()

    def test_buffers_and_advisory_availability_never_authorize_overbooking(self):
        self.book()
        b = booking('second', 'sam', '2026-10-02T11:15:00Z', '2026-10-02T12:00:00Z')
        self.assertEqual(self.c.resource_availability('projector', b['start'], b['end'], 'sam', now=NOW)['available_units'], 0)
        with self.assertRaises(ValueError):
            self.book(b, 'sam')
        b['start'] = '2026-10-02T11:30:00Z'
        self.assertEqual(self.book(b, 'sam')['status'], 'booked')

    def test_simultaneous_requests_reserve_at_most_capacity(self):
        def reserve(person):
            c = ModuleCoordinator(self.path)
            try:
                return c.book_resource(booking(person, person), person, 'concurrent verified request', now=NOW)['status']
            except ValueError:
                return 'conflict'
            finally:
                c.db.close()
        with ThreadPoolExecutor(2) as workers:
            self.assertCountEqual(list(workers.map(reserve, ['alex', 'sam'])), ['booked', 'conflict'])

    def test_capacity_uses_peak_concurrency_not_sum_of_disjoint_bookings(self):
        self.c.add_resource(resource=resource(capacity=2, buffer=0) | {'id': 'chairs'}, actor='owner', authority='custodian', now=NOW)
        for rid, start, end in [('a', '10', '11'), ('b', '11', '12')]:
            self.book(booking(rid, start=f'2026-10-02T{start}:00:00Z', end=f'2026-10-02T{end}:00:00Z') | {'resource_id': 'chairs'})
        self.assertEqual(self.book(booking('spanning', start='2026-10-02T10:00:00Z', end='2026-10-02T12:00:00Z') | {'resource_id': 'chairs'})['status'], 'booked')

    def test_unauthorized_request_and_private_booking_view_are_rejected(self):
        with self.assertRaises(ValueError):
            self.book(actor='sam')
        self.book()
        with self.assertRaises(ValueError):
            self.c.module_status('resources', 'booking-one', 'sam', now=NOW)
        with self.assertRaises(ValueError):
            self.c.cancel_booking('booking-one', 'sam', 'invalid', now=NOW)
        with self.assertRaises(ValueError):
            self.c.add_resource(resource=resource() | {'id': 'unknown'}, actor='alex', authority='calendar is not ownership', now=NOW)

    def test_external_ledger_and_unknown_policy_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            self.c.configure_module('resources', policy('external-workbook'), 'owner', now=NOW)
        with self.assertRaises(ValueError):
            self.c.configure_module('resources', policy() | {'automatic_payment': True}, 'owner', now=NOW)

    def test_notice_receipt_does_not_change_booking_and_replay_cannot_send(self):
        self.book()
        notice = self.notice()
        self.c.module_claim(notice, now=NOW)
        self.c.module_receipt(notice, 'sent', 'fictional-provider-receipt', now=NOW)
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)
        self.assertEqual(self.c.module_status('resources', 'booking-one', 'alex', now=NOW)['status'], 'booked')
        self.assertEqual(self.notice(), notice)
        later = self.c.module_notice(module='resources', record_id='booking-one', recipient='alex@example.invalid',
                                    due=(NOW + timedelta(minutes=1)).isoformat(), actor='alex', authority='repeat tick', now=NOW)
        self.assertEqual(later['id'], notice)

    def test_stop_pause_and_shared_budget_block_notice_claims(self):
        self.book()
        notice = self.notice()
        self.c.set_contact_consent('alex@example.invalid', False, 'verified STOP', now=NOW)
        with self.assertRaisesRegex(ValueError, 'consent'):
            self.c.module_claim(notice, now=NOW)
        self.c.set_contact_consent('alex@example.invalid', True, 'verified restore', now=NOW)
        with self.c.db:
            for number in range(4):
                self.c.log('email_verification_claim', str(number), {}, NOW)
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.c.module_claim(notice, now=NOW)
        p = policy(); p['enabled'] = False
        self.c.configure_module('resources', p, 'owner pause', now=NOW)
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)

    def test_module_attempt_counts_toward_other_work_and_quiet_hours(self):
        self.book()
        notice = self.notice()
        with self.assertRaisesRegex(ValueError, 'quiet'):
            self.c.module_claim(notice, now=NOW + timedelta(hours=12))
        self.c.module_claim(notice, now=NOW)
        self.assertEqual(self.c.communication_budget(now=NOW)['used'], 1)

    def test_cancellation_invalidates_pending_notice(self):
        self.book()
        notice = self.notice()
        self.c.cancel_booking('booking-one', 'owner', 'release authority', now=NOW)
        self.assertEqual(self.c.module_queue()[0]['status'], 'superseded')
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)

    def test_retention_removes_content_but_prevents_operation_replay(self):
        self.book()
        self.notice()
        result = self.c.expire_module_records('owner retention', now=NOW + timedelta(days=31))
        self.assertEqual(result['expired'], 2)
        self.assertEqual(self.c.db.execute("SELECT payload FROM module_records WHERE id='booking-one'").fetchone()[0], '{}')
        with self.assertRaises(ValueError):
            self.c.module_status('resources', 'booking-one', 'alex', now=NOW + timedelta(days=31))
        self.assertNotIn('alex', json.dumps(self.c.module_summary()))

    def test_unknown_provider_send_reconciles_without_redispatch(self):
        self.book()
        notice = self.notice()
        class Provider:
            calls = 0
            def account(self):
                return Account('fixture', 'account', 'coordinator@example.invalid', True, frozenset(), False, True, reconcile_send=True)
            def send(self, *args):
                self.calls += 1
                raise TimeoutError()
            def reconcile(self, *args):
                return SendResult('accepted', 'fixture-confirmed-receipt')
        p = Provider(); delivery = Delivery(self.c, p)
        self.assertEqual(delivery.send('module', notice, now=NOW)['status'], 'uncertain')
        self.assertEqual(delivery.reconcile('module', notice, now=NOW)['status'], 'sent')
        self.assertEqual(p.calls, 1)
