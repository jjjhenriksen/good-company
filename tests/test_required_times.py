"""Required schedule and evidence times cannot inherit the execution clock."""
import copy
from datetime import timedelta
import unittest

import test_tasks as base
from test_core import NOW, snapshot
from test_google_calendar import event
from good_company.google_calendar import GoogleCalendar
from good_company.core import stamp, iso, required_time
from good_company.onboarding import SetupCoordinator
from good_company.providers import import_complete_calendar
from good_company.cycle import run_cycle


class RequiredTimeTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_task_missing_start_preserves_existing_task(self):
        before = list(self.c.db.execute('SELECT * FROM tasks'))
        for number, missing in enumerate((None, '', False, 0)):
            with self.subTest(value=missing):
                t = base.task('missing-time-' + str(number))
                t.update(start=missing, end='2099-01-01T01:00:00Z')
                with self.assertRaises(ValueError):
                    self.c.add_task(t, 'fictional owner')
                self.assertEqual(list(self.c.db.execute('SELECT * FROM tasks')), before)

    def test_missing_availability_or_credential_time_preserves_roster(self):
        before = list(self.c.db.execute('SELECT * FROM volunteers'))
        for kind in ('availability', 'credentials'):
            for missing in (None, '', False, 0):
                with self.subTest(kind=kind, value=missing):
                    v = base.volunteer()
                    if kind == 'availability':
                        v[kind] = [{'start': missing, 'end': '2099-01-01T01:00:00Z'}]
                    else:
                        v[kind] = [{'name': 'food handling', 'issuer': 'fictional issuer',
                                    'evidence': 'fixture', 'categories': ['event preparation'],
                                    'valid_from': missing, 'valid_until': '2099-01-01T01:00:00Z'}]
                    with self.assertRaises(ValueError):
                        self.c.set_volunteer(v, 'fictional roster')
                    self.assertEqual(list(self.c.db.execute('SELECT * FROM volunteers')), before)

    def test_missing_document_date_preserves_existing_evidence(self):
        self.c.ingest('Original handbook', 'fixture', 'Handbook', NOW)
        before = list(self.c.db.execute('SELECT * FROM knowledge'))
        for missing in (None, '', False, 0):
            with self.subTest(value=missing):
                with self.assertRaises(ValueError):
                    self.c.ingest('Replacement handbook', 'fixture', 'Handbook', missing)
                self.assertEqual(list(self.c.db.execute('SELECT * FROM knowledge')), before)

    def test_missing_calendar_window_or_event_start_is_rejected(self):
        before = self.c.events()
        for field in ('window_start', 'event_start'):
            data = snapshot()
            # A short window around the real clock exercises the missing event time.
            now = stamp()
            data.update(window_start=iso(now - timedelta(days=1)),
                        window_end=iso(now + timedelta(days=1)), checked_at=iso(now))
            if field == 'window_start':
                data[field] = None
                data['events'] = []
            else:
                data['events'][0].update(start=None, end=iso(now + timedelta(hours=1)))
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.c.import_calendar(data)
                self.assertEqual(self.c.events(), before)

    def test_missing_google_event_time_is_not_replaced_with_clock(self):
        raw = copy.deepcopy(event())
        raw['start']['dateTime'] = None
        raw['end']['dateTime'] = '2099-01-01T01:00:00Z'
        with self.assertRaises(ValueError):
            GoogleCalendar._event(raw, 'fictional-calendar')

    def test_missing_conflict_window_is_not_availability_evidence(self):
        proposed = {'start': NOW, 'end': '2099-01-01T01:00:00Z'}
        with self.assertRaises(ValueError):
            self.c.conflicts(dict(proposed, start=None), [])
        with self.assertRaises(ValueError):
            self.c.conflicts(proposed, [dict(proposed, start=None)])

    def test_conflict_intervals_require_positive_duration_and_keep_boundaries(self):
        proposed = {'start': NOW, 'end': '2026-09-25T17:00:00Z'}
        for busy in ({'start': NOW, 'end': NOW},
                     {'start': proposed['end'], 'end': proposed['start']}):
            with self.subTest(busy=busy), self.assertRaises(ValueError):
                self.c.conflicts(proposed, [busy])
        self.assertTrue(self.c.conflicts(proposed, [{'start': proposed['end'], 'end': '2026-09-25T18:00:00Z'}])['available'])
        self.assertFalse(self.c.conflicts(proposed, [proposed])['available'])

    def test_missing_window_never_reads_provider(self):
        class UnusedProvider:
            def account(self):
                self.fail('An invalid window must not read a provider account')
        provider = UnusedProvider()
        provider.fail = self.fail
        for method in (lambda: import_complete_calendar(self.c, provider, 'demo-events-only', None, '2099-01-01T01:00:00Z'),
                       lambda: run_cycle(self.c, provider, 'invalid-window', None, '2099-01-01T01:00:00Z')):
            with self.assertRaises(ValueError):
                method()

    def test_undated_connection_and_retention_do_not_change_state(self):
        before = list(self.c.db.execute('SELECT * FROM settings'))
        with self.assertRaises(ValueError):
            SetupCoordinator.record_connection(self.c, 'calendar', 'verified', 'fixture evidence', None,
                                               now=stamp() + timedelta(seconds=1))
        self.assertEqual(list(self.c.db.execute('SELECT * FROM settings')), before)
        with self.assertRaises(ValueError):
            self.c.retain_delivery_history(None, 'fictional owner', now=stamp() + timedelta(days=1))

    def test_required_time_preserves_explicit_datetime_and_optional_clock(self):
        self.assertEqual(required_time(stamp(NOW), 'fixture'), stamp(NOW))
        self.assertEqual(required_time(NOW, 'fixture'), stamp(NOW))
        self.assertIsNotNone(stamp().tzinfo)
        for invalid in (None, '', ' ', False, 0, stamp(NOW).replace(tzinfo=None)):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                required_time(invalid, 'fixture')

    def test_legacy_missing_task_time_is_not_used_for_allocation(self):
        import json
        task = base.task('legacy')
        task.update(start=None, end='2099-01-01T01:00:00Z')
        with self.c.db:
            self.c.db.execute("INSERT INTO tasks VALUES(?,?,'open')", (task['id'], json.dumps(task)))
        with self.assertRaises(ValueError):
            self.c.delegate()
        self.assertEqual(self.c.task_queue(), [])
