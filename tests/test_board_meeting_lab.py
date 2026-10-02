"""Scoped online meeting and private-calendar conflict over the loopback lab."""
import json
import unittest

from loopback_mail_lab import MailLab
from good_company.apple_calendar import ApplePIMProvider
from good_company.apple_pim import NativeApplePIM
from good_company.providers import Delivery, ProviderError
from test_core import NOW, DUE, snapshot
import test_tasks as base

OBSERVED = {}


class BoardMeetingLabTests(unittest.TestCase):
    def setUp(self):
        base.TaskTests.setUp(self)
        policy = self.c.autonomy()
        policy['allowed_event_types'] = ['board meeting']
        self.c.configure_autonomy(policy, 'Fictional board remit', now=NOW)
        with self.c.db:
            self.c.db.execute('DELETE FROM dress_rules')
        self.data = snapshot()
        self.event = self.data['events'][0]
        self.event.pop('rsvp', None)
        self.event.update(title='Fictional board meeting', event_type='board meeting',
                          location='https://meet.example.invalid/board', dress_applicability='not_applicable')

    tearDown = base.TaskTests.tearDown

    def test_online_reminder_and_private_conflict_without_dress_policy(self):
        secret = 'Fictional private appointment title that must never be shared'
        busy = {'id': 'private-overlap', 'calendarId': 'lab-private-calendar', 'title': secret,
                'location': 'Fictional private place', 'isAllDay': False,
                'startDate': '2026-09-27T17:00:00-07:00', 'endDate': '2026-09-27T18:00:00-07:00'}
        with MailLab(self.tmp.name, calendars={'lab-private-calendar': [busy]}) as lab:
            self.c.import_calendar(self.data, now=NOW)
            rid = self.c.plan(now=NOW)['automatically_authorized'][0]
            reminder = self.c.reminder(rid)
            self.assertEqual(json.loads(reminder['approval'])['mode'], 'autonomous')
            self.assertNotIn('Attire:', reminder['message']['body'])
            self.assertIn('https://meet.example.invalid/board', reminder['message']['body'])
            calendar = ApplePIMProvider(NativeApplePIM(lab.port, lab.credentials['owner'], lab.root),
                'lab-account', lab.owner, 'INBOX', lab.policy_path,
                scopes={'personal-availability': 'lab-private-calendar'}, timezone='America/Los_Angeles')
            availability = calendar.availability('personal-availability', self.event['start'], self.event['end'])
            self.assertFalse(availability['available'])
            self.assertEqual(availability['message'], 'There is an existing commitment.')
            self.assertNotIn(secret, json.dumps(availability))
            self.assertNotIn('Fictional private place', json.dumps(availability))
            with self.assertRaises(ProviderError):
                calendar.availability('unselected-private-calendar', self.event['start'], self.event['end'])
            self.data['checked_at'] = DUE
            self.c.import_calendar(self.data, now=DUE)
            delivery = Delivery(self.c, lab.provider())
            delivery.send('event', rid, now=DUE)
            receipt = self.c.reminder(rid)['receipt']
            self.assertTrue(receipt.startswith('loopback-lab:'))
            self.assertEqual(lab.accepted()[0]['recipients'], ['alex@example.invalid', 'sam@example.invalid'])
            self.assertEqual(self.c.plan(now=DUE)['created'], [])
            with self.assertRaises(ValueError):
                delivery.send('event', rid, now=DUE)
            self.assertEqual(len(lab.accepted()), 1)
            self.assertEqual(self.c.db.execute('SELECT count(*) FROM dress_rules').fetchone()[0], 0)
            self.assertNotIn(secret, '\n'.join(self.c.db.iterdump()))
            OBSERVED['board'] = {'accepted_local_notices': 1, 'dress_rules_required': 0,
                'private_conflict_message': availability['message'], 'private_title_disclosed': False,
                'repeat_send_rejected': True, 'calendar_scope_enforced': True}

    def test_not_applicable_dress_does_not_authorize_an_out_of_scope_meeting(self):
        self.event['event_type'] = 'unapproved board'
        self.c.import_calendar(self.data, now=NOW)
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])
        with MailLab(self.tmp.name) as lab:
            for row in self.c.db.execute('SELECT id FROM reminders').fetchall():
                with self.assertRaises(ValueError):
                    Delivery(self.c, lab.provider()).send('event', row[0], now=DUE)
            self.assertEqual(lab.accepted(), [])
