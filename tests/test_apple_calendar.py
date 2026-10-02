import copy
import json
import unittest
from apple_pim_fixture import FictionalApplePIM
from good_company.apple_calendar import ApplePIMProvider
from good_company.providers import ProviderError, import_complete_calendar
from test_core import NOW
import test_tasks as task_base


class CalendarNative(FictionalApplePIM):
    def __init__(self, root, owner):
        super().__init__(root, owner)
        self.events = [{'id': 'native-event', 'calendarId': 'native-calendar', 'title': 'Fictional meeting',
            'startDate': '2026-09-27T00:30:00Z', 'endDate': '2026-09-27T01:30:00Z', 'isAllDay': False}]
        self.calendars = [{'id': 'native-calendar'}]
        self.payload_change = lambda data: data

    def __call__(self, domain, action, **args):
        if domain == 'mail':
            return super().__call__(domain, action, **args)
        self.calls.append((domain, action, args))
        if action == 'list':
            return {'success': True, 'calendars': copy.deepcopy(self.calendars)}, NOW
        if action == 'events':
            data = {'success': True, 'count': len(self.events), 'events': copy.deepcopy(self.events)}
            return self.payload_change(data), NOW
        raise AssertionError('Unexpected calendar action')

    def provider(self):
        return ApplePIMProvider(self, 'fixture-account', self.owner, 'INBOX', self.policy_path,
                                scopes={'demo-events-only': 'native-calendar'}, timezone='America/Los_Angeles')


class AppleCalendarTests(unittest.TestCase):
    setUp = task_base.TaskTests.setUp
    tearDown = task_base.TaskTests.tearDown

    def native(self):
        return CalendarNative(self.tmp.name, self.c.autonomy()['sender'])

    def refresh(self, native):
        return import_complete_calendar(self.c, native.provider(), 'demo-events-only',
                                        '2026-09-25T00:00:00Z', '2026-10-25T00:00:00Z', now=NOW)

    def test_exact_scope_sentinel_and_repeat_import_are_idempotent(self):
        native = self.native()
        self.refresh(native)
        self.assertEqual(self.refresh(native)['changes'], 0)
        args = [c[2] for c in native.calls if c[1] == 'events'][0]
        self.assertEqual(args['calendar'], 'native-calendar')
        self.assertEqual(args['limit'], 10001)
        self.assertNotIn('query', args)

    def test_truncated_or_mismatched_counts_preserve_previous_snapshot(self):
        native = self.native()
        self.refresh(native)
        before = self.c.events()
        for values in ({'count': 0}, {'truncated': True}, {'degraded': True}, {'count': True}):
            native.payload_change = lambda d: {**d, **values}
            with self.assertRaisesRegex(ProviderError, 'incomplete_calendar'):
                self.refresh(native)
            self.assertEqual(self.c.events(), before)

    def test_limit_sentinel_refuses_a_prefix_instead_of_retiring_absent_events(self):
        native = self.native()
        self.refresh(native)
        before = self.c.events()
        native.events *= 10001
        with self.assertRaisesRegex(ProviderError, 'incomplete_calendar'):
            self.refresh(native)
        self.assertEqual(self.c.events(), before)

    def test_recurring_identity_uses_original_occurrence_after_a_move(self):
        native = self.native()
        native.events[0].update(seriesId='series', recurrence=[{'frequency': 'weekly'}],
                                occurrenceOrigin='2026-09-27T00:30:00Z')
        first = native.provider().calendar_page('demo-events-only', '2026-09-25T00:00:00Z', '2026-10-25T00:00:00Z').events[0]
        native.events[0].update(id='changed-native-id', startDate='2026-09-28T00:30:00Z', endDate='2026-09-28T01:30:00Z')
        second = native.provider().calendar_page('demo-events-only', '2026-09-25T00:00:00Z', '2026-10-25T00:00:00Z').events[0]
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(first['source'], second['source'])
        self.assertNotEqual(first['start'], second['start'])

    def test_missing_recurrence_origin_and_ambiguous_all_day_date_are_refused(self):
        for values in ({'recurrence': [{'frequency': 'weekly'}]}, {'isAllDay': True}):
            native = self.native()
            native.events[0].update(values)
            with self.assertRaises(ProviderError):
                self.refresh(native)
            self.assertEqual(self.c.events(), [])

    def test_cross_calendar_records_and_unauthorized_inventory_are_refused(self):
        native = self.native()
        native.events[0]['calendarId'] = 'personal-calendar'
        with self.assertRaisesRegex(ProviderError, 'event_outside_calendar'):
            self.refresh(native)
        native.calendars = []
        with self.assertRaisesRegex(ProviderError, 'calendar_not_authorized'):
            native.provider().account()

    def test_complete_empty_snapshot_cancels_known_event_and_pending_work(self):
        native = self.native()
        self.refresh(native)
        self.c.plan(now=NOW)
        native.events = []
        self.refresh(native)
        self.assertEqual(self.c.events()[0]['cancelled'], 1)
        self.assertTrue(all(r['status'] not in ('draft', 'approved') for r in self.c.queue()))

    def test_conflict_projection_never_discloses_private_title(self):
        native = self.native()
        native.events[0]['title'] = 'Private medical appointment'
        result = native.provider().availability('demo-events-only', '2026-09-27T01:00:00Z', '2026-09-27T02:00:00Z')
        self.assertFalse(result['available'])
        self.assertNotIn('medical', json.dumps(result))

    def test_outbound_capability_and_receipts_are_not_invented(self):
        native = self.native()
        provider = native.provider()
        identity = provider.account()
        self.assertFalse(identity.unattended_send)
        self.assertFalse(identity.idempotent_send)
        self.assertFalse(identity.reconcile_send)
        with self.assertRaisesRegex(ProviderError, 'receipt_unavailable'):
            provider.send({}, 'test-operation')
        self.assertNotIn('send', [c[1] for c in native.calls])
