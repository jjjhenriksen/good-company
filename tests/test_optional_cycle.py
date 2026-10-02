from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from good_company.cycle import run_cycle
from good_company.providers import SendResult
from module_fixture import NOW, booking, coordinator, resource
from test_providers import FixtureProvider


class OptionalCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = coordinator(Path(self.tmp.name) / 'state.sqlite')
        self.c.add_resource(resource(), 'owner', 'fictional custodian', now=NOW)
        self.c.book_resource(booking(), 'alex', 'verified request', now=NOW)
        self.c.module_notice('resources', 'booking-one', 'alex@example.invalid', NOW.isoformat(),
                             'owner', 'fictional notice authority', now=NOW)
        self.p = FixtureProvider()
        self.p.pages = [replace(self.p.pages[0], events=[], checked_at=NOW.isoformat(), next_cursor=None)]

    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()

    def cycle(self, tick):
        return run_cycle(self.c, self.p, tick, NOW.isoformat(), (NOW + timedelta(days=7)).isoformat(), now=NOW)

    def test_operational_cycle_delivers_optional_notice_once(self):
        result = self.cycle('first')
        self.assertEqual(result['sent'], 1)
        self.assertEqual(self.cycle('second')['sent'], 0)
        self.assertEqual(len(self.p.sent), 1)
        self.assertEqual(self.c.module_status('resources', 'booking-one', 'alex', now=NOW)['status'], 'booked')

    def test_operational_cycle_reconciles_unknown_optional_notice(self):
        self.p.result = TimeoutError()
        self.assertEqual(self.cycle('first')['uncertain'], 1)
        self.p.result = SendResult('accepted', 'fixture-reconciled')
        self.assertEqual(self.cycle('second')['reconciled'], 1)
        self.assertEqual(len(self.p.sent), 1)

    def test_paused_cycle_still_expires_private_records_without_provider_calls(self):
        policy = self.c.autonomy(); policy['enabled'] = False
        self.c.configure_autonomy(policy, 'owner pause', now=NOW)
        later = NOW + timedelta(days=31)
        with patch.object(self.p, 'account', side_effect=AssertionError('must not connect')):
            result = run_cycle(self.c, self.p, 'paused', later.isoformat(), (later + timedelta(days=7)).isoformat(), now=later)
        self.assertEqual(result['status'], 'paused')
        self.assertEqual(self.c.db.execute("SELECT payload FROM module_records WHERE id='booking-one'").fetchone()[0], '{}')
