import unittest
import test_tasks as base
from test_core import NOW
from good_company.tasks import WorkCoordinator


class ConsentTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_stop_blocks_queued_tasks_and_survives_roster_update(self):
        self.c.delegate(now=NOW)
        nid = next(n['id'] for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.set_contact_consent('ALEX@example.invalid', False, 'verified stop', now=NOW)
        self.c.set_volunteer(base.volunteer(), 'roster refresh', now=NOW)
        self.c.delegate(now=NOW)
        with self.assertRaises(ValueError):
            self.c.task_claim(nid, now=NOW)
        self.assertTrue(self.c.contact_allowed('sam@example.invalid'))
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))

    def test_explicit_restore_and_persistence(self):
        self.c.set_contact_consent('alex@example.invalid', False, 'verified stop', now=NOW)
        self.c.db.close()
        self.c = WorkCoordinator(base.Path(self.tmp.name) / 'tasks.sqlite')
        self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
        with self.assertRaises(ValueError):
            self.c.set_contact_consent('alex@example.invalid', True, '', now=NOW)
        self.c.set_contact_consent('alex@example.invalid', True, 'verified new consent', now=NOW)
        self.assertTrue(self.c.contact_allowed('alex@example.invalid'))

    def test_event_recipient_resolution_excludes_stopped_contact(self):
        self.c.set_contact_consent('alex@example.invalid', False, 'verified stop', now=NOW)
        self.assertEqual(self.c._event_recipients(self.c.autonomy(), {}), ['sam@example.invalid'])

import test_autonomy as event_base
from test_core import DUE


class EventConsentTests(unittest.TestCase):
    setUp = event_base.AutonomyTests.setUp
    tearDown = event_base.AutonomyTests.tearDown

    def test_stop_invalidates_queued_event_then_unaffected_recipient_can_send(self):
        old = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.c.set_contact_consent('alex@example.invalid', False, 'verified stop', now=NOW)
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        with self.assertRaises(ValueError):
            self.c.claim(old, now=DUE)
        fresh = self.c.plan(now=DUE)['automatically_authorized'][0]
        self.assertEqual(self.c.claim(fresh, now=DUE)['message']['bcc'], ['sam@example.invalid'])
