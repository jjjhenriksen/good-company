import copy
import json
from pathlib import Path
import tempfile
import unittest

from good_company.core import Coordinator
from good_company.google_calendar import GoogleCalendar
from test_core import NOW, DUE


class EventContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = Coordinator(Path(self.tmp.name) / 'state.sqlite')
        self.c.configure(json.loads(Path('examples/profile.json').read_text())['profile'])
        self.policy = json.loads(Path('examples/autonomy.json').read_text())['policy']
        self.context = {'source': 'fictional://owner/board-instructions',
                        'event_type': 'service activity', 'dress_applicability': 'not_applicable',
                        'location': 'Fictional online meeting; no attendance requested'}
        self.policy['event_contexts'] = {'demo-events-only': {'board-instance': self.context}}
        self.c.configure_autonomy(self.policy, 'fictional owner instructions', now=NOW)
        raw = {'id': 'board-instance', 'summary': 'Fictional board meeting', 'status': 'confirmed',
               'start': {'dateTime': '2026-09-27T12:00:00-07:00'},
               'end': {'dateTime': '2026-09-27T13:00:00-07:00'}}
        self.event = GoogleCalendar._event(raw, 'fixture-calendar')
        self.snapshot = {'calendar': 'demo-events-only', 'complete': True, 'checked_at': NOW,
                         'window_start': '2026-09-25T00:00:00Z', 'window_end': '2026-10-01T00:00:00Z',
                         'events': [self.event]}

    def tearDown(self):
        self.c.db.close()
        self.tmp.cleanup()

    def test_normalized_event_gets_cited_context_and_survives_refresh(self):
        self.c.import_calendar(self.snapshot, now=NOW)
        self.c.plan(now=NOW)
        notice = self.c.queue()[0]
        self.assertEqual(notice['status'], 'approved')
        message = self.c.reminder(notice['id'])['message']
        self.assertEqual(message['missing'], [])
        self.assertIn(self.context['source'], message['sources'])
        self.assertNotIn('Attire:', message['body'])
        self.assertEqual(self.c.import_calendar(self.snapshot, now=NOW)['changes'], 0)
        self.assertEqual(self.c.plan(now=NOW)['created'], [])
        self.assertNotIn('event_type', self.event)  # caller/provider data unchanged

    def test_calendar_location_and_cancellation_stay_authoritative(self):
        self.c.import_calendar(self.snapshot, now=NOW)
        self.c.plan(now=NOW)
        self.snapshot['events'][0].update(location='Changed calendar venue', status='cancelled')
        self.snapshot['checked_at'] = DUE
        self.c.import_calendar(self.snapshot, now=DUE)
        saved = self.c.events()[0]
        self.assertTrue(saved['cancelled'])
        self.assertEqual(saved['payload']['location'], 'Changed calendar venue')
        self.assertEqual(self.c.plan(now=DUE)['created'], [])
        self.assertFalse(any(n['status'] == 'approved' for n in self.c.queue()))

    def test_context_does_not_apply_to_another_instance_or_calendar(self):
        self.snapshot['events'][0]['id'] = 'other-instance'
        self.c.import_calendar(self.snapshot, now=NOW)
        self.assertNotIn('event_type', self.c.events()[0]['payload'])
        self.snapshot['events'][0]['id'] = 'board-instance'
        self.snapshot['calendar'] = 'another-calendar'
        self.c.import_calendar(self.snapshot, now=NOW)
        for event in self.c.events():
            self.assertNotIn('event_type', event['payload'])

    def test_removal_invalidates_approval_and_refresh_removes_context(self):
        self.c.import_calendar(self.snapshot, now=NOW)
        self.c.plan(now=NOW)
        del self.policy['event_contexts']
        self.c.configure_autonomy(self.policy, 'fictional owner withdrew context', now=NOW)
        self.assertFalse(any(n['status'] == 'approved' for n in self.c.queue()))
        self.c.import_calendar(self.snapshot, now=NOW)
        self.assertNotIn('event_type', self.c.events()[0]['payload'])
        self.assertNotIn('detail_sources', self.c.events()[0]['payload'])

    def test_retired_owner_source_prevents_automatic_authorization(self):
        self.c.import_calendar(self.snapshot, now=NOW)
        self.c.withdraw_source(self.context['source'], 'fictional withdrawal', now=NOW)
        self.c.plan(now=NOW)
        self.assertFalse(any(n['status'] == 'approved' for n in self.c.queue()))
        self.assertTrue(any('Retired source' in reason for reason in self.c.reminder(self.c.queue()[0]['id'])['message']['missing']))

    def test_unsafe_context_rejected_without_settings_changes(self):
        bad = [dict(self.context, start=NOW), dict(self.context, status='confirmed'),
               dict(self.context, to=['outside@example.invalid']), dict(self.context, source=''),
               dict(self.context, event_type='outside remit'), dict(self.context, mixed_role_audience='yes')]
        for context in bad:
            policy = copy.deepcopy(self.policy)
            policy['event_contexts']['demo-events-only']['board-instance'] = context
            before = self.c.autonomy()
            with self.assertRaises(ValueError):
                self.c.configure_autonomy(policy, 'fixture', now=NOW)
            self.assertEqual(self.c.autonomy(), before)
        for scope, uid in [('outside', 'board-instance'), ('demo-events-only', '*')]:
            policy = copy.deepcopy(self.policy)
            policy['event_contexts'] = {scope: {uid: self.context}}
            with self.assertRaises(ValueError):
                self.c.configure_autonomy(policy, 'fixture', now=NOW)
