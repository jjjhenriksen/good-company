from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from io import StringIO

import test_tasks as fixtures
from test_core import NOW, snapshot
from test_providers import FixtureProvider
from good_company.cycle import run_cycle, cycle_lock
from good_company.onboarding import SetupCoordinator
from good_company.providers import ProviderError, SendResult


class CycleTests(unittest.TestCase):
    def setUp(self):
        fixtures.TaskTests.setUp(self)
        path = Path(self.tmp.name) / 'tasks.sqlite'
        self.c.db.close()
        self.c = SetupCoordinator(path)
        self.p = FixtureProvider()
        self.window = snapshot()

    tearDown = fixtures.TaskTests.tearDown

    def run_cycle(self, cycle='tick-one'):
        return run_cycle(self.c, self.p, cycle, self.window['window_start'], self.window['window_end'], now=NOW)

    def test_cycle_allocates_and_sends_assignment_once_across_ticks(self):
        result = self.run_cycle()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['sent'], 1)
        self.assertTrue(self.run_cycle()['replayed'])
        self.assertEqual(self.run_cycle('tick-two')['sent'], 0)
        self.assertEqual(len(self.p.sent), 1)
        notice = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.assertEqual(notice['status'], 'sent')

    def test_ambiguous_send_reconciles_on_next_tick_without_resend(self):
        self.p.result = TimeoutError('private result')
        self.assertEqual(self.run_cycle()['uncertain'], 1)
        self.p.result = SendResult('accepted', 'fixture-later-receipt')
        self.assertEqual(self.run_cycle('tick-two')['reconciled'], 1)
        self.assertEqual(len(self.p.sent), 1)

    def test_paused_cycle_never_contacts_provider_or_allocates(self):
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'pause', now=NOW)
        with patch.object(self.p, 'account', side_effect=AssertionError('must not connect')):
            self.assertEqual(self.run_cycle()['status'], 'paused')
        self.assertEqual(self.c.task_queue(), [])

    def test_missing_send_permission_leaves_work_unclaimed(self):
        self.p.identity = replace(self.p.identity, unattended_send=False)
        self.assertEqual(self.run_cycle()['status'], 'blocked')
        self.assertEqual(self.c.task_queue(), [])
        self.assertEqual(self.p.sent, [])

    def test_incomplete_second_scope_prevents_all_delivery(self):
        policy = self.c.autonomy()
        policy['calendar_scopes'].append('second')
        self.c.configure_autonomy(policy, 'second scope', now=NOW)
        self.p.identity = replace(self.p.identity, calendar_scopes=frozenset(policy['calendar_scopes']))
        original = self.p.calendar_page

        def page(scope, *args):
            if scope == 'second':
                raise ProviderError('pending')
            return original(scope, *args)

        self.p.calendar_page = page
        self.assertEqual(self.run_cycle()['refreshed_scopes'], 1)
        self.assertEqual(self.p.sent, [])
        self.assertEqual(self.c.task_queue(), [])

    def test_two_workers_do_not_overlap_and_lock_releases(self):
        with cycle_lock(self.c) as locked:
            self.assertTrue(locked)
            self.assertEqual(self.run_cycle()['status'], 'already_running')
        self.assertEqual(self.run_cycle()['status'], 'completed')

    def test_changed_configuration_cannot_replay_old_cycle(self):
        self.run_cycle()
        profile = self.c.profile()
        profile['organization'] = 'Changed fictional group'
        self.c.configure(profile)
        with self.assertRaises(ProviderError):
            self.run_cycle()

    def test_interrupted_cycle_resumes_without_resending_claimed_notice(self):
        with patch.object(self.c, 'task_receipt', side_effect=RuntimeError('simulated crash after provider accepted')):
            with self.assertRaises(RuntimeError):
                self.run_cycle()
        self.assertEqual(self.run_cycle()['reconciled'], 1)
        self.assertEqual(len(self.p.sent), 1)

    def test_summary_contains_no_recipient_or_body(self):
        self.run_cycle()
        saved = self.c.db.execute('SELECT summary FROM operational_cycles').fetchone()[0]
        self.assertNotIn('@', saved)
        self.assertNotIn('Prepare the welcome', saved)

    def test_cli_without_unattended_authority_never_opens_connection(self):
        from good_company.cycle_cli import main
        config = Path(self.tmp.name) / 'cycle.json'
        config.write_text(json.dumps({'db': 'tasks.sqlite', 'journal': 'latch.sqlite',
                                      'account': 'coordinator@example.invalid', 'scopes': {'scope': 'cal'}}))
        args = ['good-company-cycle', '--config', str(config), '--cycle-id', 'one',
                '--start', self.window['window_start'], '--end', self.window['window_end']]
        with patch('sys.argv', args), patch('sys.stdout', new_callable=StringIO) as output, \
             patch('good_company.cycle_cli.LatchMCP', side_effect=AssertionError('must not connect')):
            self.assertEqual(main(), 2)
            self.assertEqual(json.loads(output.getvalue())['status'], 'blocked')
