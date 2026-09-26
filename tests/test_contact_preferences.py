import unittest
import test_tasks as base
from test_core import NOW
from good_company.core import stamp


class PreferenceTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def prefs(self, **changes):
        return dict(timezone='America/Los_Angeles', channels=['email'], quiet_start=21, quiet_end=7, min_interval_hours=2, **changes)

    def test_both_queues_share_cadence(self):
        self.c.set_contact_preferences('alex@example.invalid', self.prefs(), 'verified preference', now=NOW)
        message = {'to': ['alex@example.invalid']}
        with self.c.db:
            self.c._record_contacts('event', 'prior', message, stamp(NOW))
        self.c.delegate(now=NOW)
        notice = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        with self.assertRaisesRegex(ValueError, 'cadence'):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == notice['id'])['status'], 'pending')

    def test_recipient_timezone_and_dst(self):
        prefs = self.prefs()
        prefs['timezone'] = 'America/New_York'
        self.c.set_contact_preferences('alex@example.invalid', prefs, 'verified preference', now=NOW)
        message = {'bcc': ['alex@example.invalid']}
        with self.assertRaisesRegex(ValueError, 'quiet'):
            self.c._check_contacts(message, stamp('2026-07-01T10:30:00Z'))
        self.c._check_contacts(message, stamp('2026-07-01T11:00:00Z'))
        with self.assertRaisesRegex(ValueError, 'quiet'):
            self.c._check_contacts(message, stamp('2026-12-01T11:30:00Z'))
        self.c._check_contacts(message, stamp('2026-12-01T12:00:00Z'))

    def test_preferences_do_not_restore_consent(self):
        self.c.set_contact_consent('alex@example.invalid', False, 'verified stop', now=NOW)
        self.c.set_contact_preferences('alex@example.invalid', self.prefs(), 'verified preference', now=NOW)
        with self.assertRaisesRegex(ValueError, 'consent'):
            self.c._check_contacts({'to': ['alex@example.invalid']}, stamp(NOW))

    def test_unsupported_channel_is_not_silently_used(self):
        prefs = self.prefs()
        prefs['channels'] = []
        self.c.set_contact_preferences('alex@example.invalid', prefs, 'verified preference', now=NOW)
        with self.assertRaisesRegex(ValueError, 'channel'):
            self.c._check_contacts({'to': ['alex@example.invalid']}, stamp(NOW))
