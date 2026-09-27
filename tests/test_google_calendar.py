import copy
import json
from pathlib import Path
import tempfile
import unittest

from good_company.core import Coordinator, stamp
from good_company.google_calendar import GoogleCalendar
from good_company.latch import LatchOperations
from good_company.providers import ProviderError, import_complete_calendar

ACCOUNT = 'owner@example.invalid'
START, END = '2026-09-25T00:00:00Z', '2026-10-25T00:00:00Z'


def event(uid='instance-1'):
    return {'id': uid, 'summary': 'Fictional rehearsal', 'status': 'confirmed',
            'start': {'dateTime': '2026-09-27T10:00:00-07:00'},
            'end': {'dateTime': '2026-09-27T11:00:00-07:00'},
            'recurringEventId': 'series', 'originalStartTime': {'dateTime': '2026-09-27T10:00:00-07:00'}}


class GoogleCalendarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.calls = []
        self.data = {'events': [event()], 'nextPageToken': ''}
        self.ops = LatchOperations(Path(self.tmp.name) / 'journal.sqlite', self.call)
        self.provider = GoogleCalendar(self.ops, ACCOUNT, {'demo-events-only': 'calendar-id'}, 'cycle-1')

    def tearDown(self):
        self.ops.close()
        self.tmp.cleanup()

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        argv = arguments['argv']
        if argv == ['plow-gog', 'accounts']:
            result = {'status': 'completed', 'accounts': [{'account': ACCOUNT}], 'degraded': []}
        else:
            result = {'status': 'completed', 'exit_code': 0, 'output': json.dumps(self.data)}
        return {'structuredContent': result}

    def test_account_scope_and_no_implicit_send_permission(self):
        account = self.provider.account()
        self.assertTrue(account.authenticated)
        self.assertFalse(account.unattended_send)
        page = self.provider.calendar_page('demo-events-only', START, END)
        self.assertEqual(page.events[0]['id'], 'instance-1')
        argv = self.calls[-1][1]['argv']
        self.assertEqual(argv[3], 'calendar-id')
        self.assertEqual(argv[argv.index('--account') + 1], ACCOUNT)
        self.assertNotIn('--all-pages', argv)
        with self.assertRaises(ProviderError):
            self.provider.calendar_page('outside', START, END)

    def test_resume_keeps_original_observation_and_does_not_refetch(self):
        first = self.provider.calendar_page('demo-events-only', START, END)
        second = self.provider.calendar_page('demo-events-only', START, END)
        self.assertEqual(first, second)
        self.assertEqual(len(self.calls), 1)

    def test_distinct_cycle_refreshes_and_cursor_is_preserved(self):
        self.data['nextPageToken'] = 'opaque-cursor'
        first = self.provider.calendar_page('demo-events-only', START, END)
        self.data = {'events': [], 'nextPageToken': ''}
        self.provider.calendar_page('demo-events-only', START, END, first.next_cursor)
        self.assertEqual(self.calls[-1][1]['argv'][-2:], ['--page', 'opaque-cursor'])
        fresh = GoogleCalendar(self.ops, ACCOUNT, {'demo-events-only': 'calendar-id'}, 'cycle-2')
        fresh.calendar_page('demo-events-only', START, END)
        self.assertEqual(len(self.calls), 3)

    def test_incomplete_fanout_and_unexpanded_events_rejected(self):
        bad = [{'items': [], 'degraded': []}, {'events': []},
               {'events': [], 'nextPageToken': '', 'truncated': {'omitted': 1}},
               {'events': [], 'nextPageToken': '', 'degraded': ['unavailable']},
               {'events': [dict(event(), recurrence=['RRULE:FREQ=WEEKLY'])], 'nextPageToken': ''}]
        for i, payload in enumerate(bad):
            with self.subTest(i=i):
                self.data = payload
                self.provider.cycle_id = str(i)
                with self.assertRaises(ProviderError):
                    self.provider.calendar_page('demo-events-only', START, END)

    def test_overlap_start_outside_window_is_excluded(self):
        self.data['events'][0]['start']['dateTime'] = '2026-09-24T10:00:00Z'
        self.assertEqual(self.provider.calendar_page('demo-events-only', START, END).events, [])

    def test_moved_instance_preserves_provider_id_and_rejects_naive_time(self):
        original = event()
        moved = copy.deepcopy(original)
        moved['start']['dateTime'] = '2026-09-27T10:30:00-07:00'
        self.assertEqual(GoogleCalendar._event(original, 'cal')['id'], GoogleCalendar._event(moved, 'cal')['id'])
        moved['start']['dateTime'] = '2026-09-27T10:30:00'
        with self.assertRaises(ProviderError):
            GoogleCalendar._event(moved, 'cal')

    def test_complete_calendar_import_uses_time_after_provider_read(self):
        from test_core import snapshot
        c = Coordinator(Path(self.tmp.name) / 'state.sqlite')
        try:
            c.configure(json.loads(Path('examples/profile.json').read_text())['profile'])
            c.configure_autonomy(json.loads(Path('examples/autonomy.json').read_text())['policy'], 'fixture owner')
            result = import_complete_calendar(c, self.provider, 'demo-events-only', START, END)
            self.assertEqual(result['imported'], 1)
        finally:
            c.db.close()

    def test_multiday_all_day_exclusive_end_survives_import(self):
        self.data['events'] = [dict(event(), start={'date': '2026-09-27'}, end={'date': '2026-09-30'})]
        c = Coordinator(Path(self.tmp.name) / 'all-day.sqlite')
        try:
            c.configure(json.loads(Path('examples/profile.json').read_text())['profile'])
            c.configure_autonomy(json.loads(Path('examples/autonomy.json').read_text())['policy'], 'fixture owner')
            import_complete_calendar(c, self.provider, 'demo-events-only', START, END)
            row = c.db.execute('SELECT start,end FROM events').fetchone()
            self.assertEqual((stamp(row['end']) - stamp(row['start'])).days, 3)
        finally:
            c.db.close()
