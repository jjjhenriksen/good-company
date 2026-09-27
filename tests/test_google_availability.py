from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from good_company.core import stamp
from good_company.google_calendar import GoogleCalendar
from good_company.latch import LatchOperations
from good_company.providers import ProviderError


ACCOUNT = 'owner@example.invalid'
CALENDAR = 'personal@example.invalid'
START, END = '2026-09-28T17:00:00Z', '2026-09-28T18:00:00Z'


class GoogleAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.calls = []
        self.data = {'calendars': {CALENDAR: {'busy': [{'start': START, 'end': END}]}}}
        self.accounts = [{'account': ACCOUNT}]
        self.ops = LatchOperations(Path(self.tmp.name) / 'journal.sqlite', self.call)
        self.provider = GoogleCalendar(self.ops, ACCOUNT, {'personal-busy': CALENDAR}, 'check-1')

    def tearDown(self):
        self.ops.close()
        self.tmp.cleanup()

    def call(self, name, arguments):
        argv = arguments['argv']
        self.calls.append(argv)
        if argv == ['plow-gog', 'accounts']:
            payload = {'status': 'completed', 'accounts': self.accounts}
        else:
            payload = {'status': 'completed', 'exit_code': 0, 'output': json.dumps(self.data)}
        return {'structuredContent': payload}

    def check(self, **kwargs):
        return self.provider.check_availability('personal-busy', START, END, **kwargs)

    def test_conflict_uses_only_freebusy_and_returns_no_calendar_or_intervals(self):
        result = self.check()
        self.assertFalse(result['available'])
        self.assertEqual(result['message'], 'There is an existing commitment.')
        self.assertEqual(set(result), {'available', 'checked_at', 'message', 'scope'})
        self.assertNotIn(CALENDAR, json.dumps(result))
        self.assertNotIn(START, json.dumps(result))
        self.assertEqual(self.calls, [
            ['plow-gog', 'accounts'],
            ['plow-gog', 'calendar', 'freebusy', CALENDAR, '--account', ACCOUNT,
             '--from', '2026-09-28T17:00:00+00:00', '--to', '2026-09-28T18:00:00+00:00', '--json']])

    def test_explicit_empty_and_omitted_empty_busy_list_are_available(self):
        for i, value in enumerate(({'busy': []}, {})):
            self.data = {'calendars': {CALENDAR: value}}
            self.provider.cycle_id = str(i)
            self.assertTrue(self.check()['available'])

    def test_replay_keeps_observation_without_reading_again(self):
        first = self.check()
        self.assertEqual(self.check(), first)
        self.assertEqual(len(self.calls), 2)

    def test_wrong_scope_and_ambiguous_selectors_never_dispatch(self):
        with self.assertRaises(ProviderError):
            self.provider.check_availability('outside', START, END)
        for calendar in ('1', 'Personal', '--all', 'a@example.invalid,b@example.invalid'):
            self.provider.scopes['personal-busy'] = calendar
            with self.assertRaisesRegex(ProviderError, 'explicit_availability'):
                self.check()
        self.assertEqual(self.calls, [])

    def test_primary_is_bound_to_the_explicit_authenticated_account(self):
        self.provider.scopes['personal-busy'] = 'primary'
        self.data = {'calendars': {ACCOUNT: {'busy': []}}}
        self.assertTrue(self.check()['available'])
        self.assertEqual(self.calls[-1][3], ACCOUNT)

    def test_invalid_windows_never_dispatch(self):
        for first, last in ((None, END), (START, START), (END, START),
                            ('2026-09-28T17:00:00', END), (START, '2027-09-28T18:00:00Z')):
            with self.subTest(first=first, last=last), self.assertRaisesRegex(ProviderError, 'invalid_availability_window'):
                self.provider.check_availability('personal-busy', first, last)
        self.assertEqual(self.calls, [])

    def test_missing_account_never_reads_availability(self):
        self.accounts = []
        with self.assertRaisesRegex(ProviderError, 'account_unavailable'):
            self.check()
        self.assertEqual(self.calls, [['plow-gog', 'accounts']])

    def test_wrong_missing_or_partial_results_never_report_free(self):
        bad = [{}, {'calendars': {}}, {'calendars': {'other@example.invalid': {}}},
               {'calendars': {CALENDAR: {}, 'other@example.invalid': {}}},
               {'calendars': {CALENDAR: {'errors': [{'reason': 'notFound'}]}}},
               {'calendars': {CALENDAR: {'busy': None}}},
               {'calendars': {CALENDAR: {'busy': [], 'summary': 'PRIVATE EVENT TITLE'}}},
               {'calendars': {CALENDAR: {}}, 'truncated': True}]
        for i, data in enumerate(bad):
            with self.subTest(i=i):
                self.data = data
                self.provider.cycle_id = str(i)
                with self.assertRaises(ProviderError) as caught:
                    self.check()
                self.assertNotIn('PRIVATE EVENT TITLE', str(caught.exception))

    def test_invalid_busy_intervals_never_report_free(self):
        bad = [None, {}, {'start': END, 'end': START},
               {'start': '2026-09-28T17:00:00', 'end': END},
               {'start': '2026-09-29T17:00:00Z', 'end': '2026-09-29T18:00:00Z'},
               {'start': START, 'end': END, 'title': 'PRIVATE EVENT TITLE'}]
        for i, interval in enumerate(bad):
            self.data = {'calendars': {CALENDAR: {'busy': [interval]}}}
            self.provider.cycle_id = str(i)
            with self.subTest(i=i), self.assertRaisesRegex(ProviderError, 'intervals_unconfirmed'):
                self.check()

    def test_stale_and_future_observations_require_a_fresh_check(self):
        observed = stamp(self.check()['checked_at'])
        for now in (observed + timedelta(minutes=16), observed - timedelta(seconds=1)):
            with self.assertRaisesRegex(ProviderError, 'observation_not_current'):
                self.check(now=now)
        self.assertEqual(len(self.calls), 2)
