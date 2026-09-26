import json
from pathlib import Path
import unittest
import test_core as base
from test_core import NOW, DUE, snapshot


class AutonomyTests(unittest.TestCase):
    tearDown = base.CoordinationTests.tearDown
    def setUp(self):
        base.CoordinationTests.setUp(self)
        self.policy = json.loads(Path('examples/autonomy.json').read_text())
        self.c.configure_autonomy(**self.policy, now=NOW)
        self.c.set_dress_code(**json.loads(Path('examples/dress-code.json').read_text()), now=NOW)
        self.data = snapshot()
        self.data['events'][0].update(event_type='service activity', dress_code_role='member')
        self.c.import_calendar(self.data, now=NOW)

    # Inherited base tests run separately; only exercise the new autonomy behavior here.
    def test_routine_reminder_authorizes_without_human_review(self):
        result = self.c.plan(now=NOW)
        rid = result['automatically_authorized'][0]
        item = self.c.reminder(rid)
        self.assertEqual(item['status'], 'approved')
        self.assertEqual(json.loads(item['approval'])['mode'], 'autonomous')
        self.assertEqual(item['message']['bcc'], self.policy['policy']['reminder_recipients'])
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        self.assertEqual(self.c.claim(rid, now=DUE)['message']['sender'], 'coordinator@example.invalid')

    def test_pause_cancels_pending_automatic_authorization(self):
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.policy['policy']['enabled'] = False
        self.c.configure_autonomy(**self.policy, now=NOW)
        self.assertEqual(self.c.reminder(rid)['status'], 'superseded')
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_unknown_location_becomes_exception(self):
        del self.data['events'][0]['location']
        self.c.import_calendar(self.data, now=NOW)
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_outside_calendar_scope_is_not_auto_authorized(self):
        self.policy['policy']['calendar_scopes'] = ['different-calendar']
        self.c.configure_autonomy(**self.policy, now=NOW)
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_event_change_replans_without_routine_human_review(self):
        old = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.data['events'][0]['location'] = 'Updated demo venue'
        self.c.import_calendar(self.data, now=NOW)
        new = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.assertNotEqual(old, new)
        self.assertEqual(self.c.reminder(old)['status'], 'superseded')

    def test_daily_limit_blocks_excess_routine_mail(self):
        self.policy['policy']['max_reminders_per_day'] = 1
        self.c.configure_autonomy(**self.policy, now=NOW)
        second = dict(self.data['events'][0]); second['id'] = 'second-event'
        self.data['events'].append(second)
        self.c.import_calendar(self.data, now=NOW)
        ids = self.c.plan(now=NOW)['automatically_authorized']
        self.data['checked_at'] = DUE; self.c.import_calendar(self.data, now=DUE)
        self.c.claim(ids[0], now=DUE)
        with self.assertRaisesRegex(ValueError, 'cadence'): self.c.claim(ids[1], now=DUE)

