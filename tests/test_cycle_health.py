from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import test_readiness as base
from test_core import NOW, snapshot
from test_providers import FixtureProvider
from test_tasks import task
from good_company.core import stamp
from good_company.cycle import run_cycle
from good_company.providers import ProviderError


class CycleHealthTests(unittest.TestCase):
    setUp = base.ReadinessTests.setUp
    tearDown = base.ReadinessTests.tearDown
    configured = base.ReadinessTests.configured

    def cycle(self, cycle_id='PRIVATE-CYCLE-ID', blocked=False, now=NOW):
        provider = FixtureProvider()
        provider.pages = [replace(provider.pages[0], events=[], checked_at=now)]
        window = snapshot()
        if blocked:
            with patch.object(provider, 'calendar_page', side_effect=ProviderError('PRIVATE-PROVIDER-ERROR')):
                return run_cycle(self.c, provider, cycle_id, window['window_start'], window['window_end'], now=now)
        return run_cycle(self.c, provider, cycle_id, window['window_start'], window['window_end'], now=now)

    def test_recorded_blocked_cycle_overrides_fresh_connection_attestations(self):
        self.configured()
        self.assertTrue(self.c.readiness(now=NOW)['ready'])
        self.assertEqual(self.cycle(blocked=True)['status'], 'blocked')
        state = self.c.readiness(now=NOW)
        self.assertFalse(state['ready'])
        self.assertEqual(state['latest_cycle']['status'], 'blocked')
        self.assertEqual(state['connections']['calendar']['status'], 'verified')
        self.assertNotIn('PRIVATE-', json.dumps(state))

    def test_same_failure_stays_quiet_and_later_success_reports_recovery(self):
        self.configured()
        self.assertFalse(self.c.health(now=NOW)['notify'])
        self.cycle('first-private-id', blocked=True)
        self.assertTrue(self.c.health(now=NOW)['notify'])
        later = stamp(NOW) + timedelta(minutes=1)
        self.cycle('second-private-id', blocked=True, now=later)
        self.assertFalse(self.c.health(now=later)['notify'])
        recovered = later + timedelta(minutes=1)
        self.cycle('recovered-private-id', now=recovered)
        report = self.c.health(now=recovered)
        self.assertTrue(report['health']['ready'], report)
        self.assertTrue(report['notify'])
        self.assertFalse(self.c.health(now=recovered)['notify'])
        self.assertNotIn('private-id', json.dumps(report))

    def test_completed_cycle_with_planning_exceptions_is_not_clean(self):
        self.configured()
        self.c.add_task(task(), 'fictional task with no roster', now=NOW)
        result = self.cycle()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['planning_exceptions'], 1)
        state = self.c.readiness(now=NOW)
        self.assertFalse(state['ready'])
        self.assertEqual(state['latest_cycle']['planning_exceptions'], 1)
        self.assertNotIn('chairs', json.dumps(state))

    def test_incomplete_cycle_does_not_inherit_previous_success(self):
        self.configured()
        self.cycle('complete')
        with self.c.db:
            self.c.db.execute("INSERT INTO operational_cycles VALUES('PRIVATE-INTERRUPTED','private-fingerprint','running',?,NULL,NULL)",
                              ((stamp(NOW) + timedelta(seconds=1)).isoformat(),))
        state = self.c.readiness(now=stamp(NOW) + timedelta(seconds=1))
        self.assertFalse(state['ready'])
        self.assertEqual(state['latest_cycle']['status'], 'running')
        self.assertIsNone(state['latest_cycle']['finished_at'])
        self.assertNotIn('PRIVATE-', json.dumps(state))

    def test_resumed_older_cycle_reports_its_newer_failed_outcome(self):
        self.configured()
        self.cycle('older', blocked=True)
        self.cycle('newer', now=stamp(NOW) + timedelta(minutes=1))
        later = stamp(NOW) + timedelta(minutes=2)
        self.cycle('older', blocked=True, now=later)
        state = self.c.readiness(now=later)
        self.assertFalse(state['ready'])
        self.assertEqual(state['latest_cycle']['status'], 'blocked')
        self.assertEqual(state['latest_cycle']['finished_at'], later.isoformat())
