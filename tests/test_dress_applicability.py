import unittest
import test_autonomy as base
from test_core import NOW, DUE


class ApplicabilityTests(unittest.TestCase):
    setUp = base.AutonomyTests.setUp
    tearDown = base.AutonomyTests.tearDown

    def test_not_applicable_can_send_without_rules(self):
        event = self.data['events'][0]
        event.pop('attire', None)
        event['dress_applicability'] = 'not_applicable'
        self.c.set_dress_code('demo-dress-policy', [], 'withdrawal', now=NOW)
        self.c.db.execute('DELETE FROM dress_rules')
        self.c.db.commit()
        self.c.import_calendar(self.data, now=NOW)
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        self.assertNotIn('Attire:', self.c.claim(rid, now=DUE)['message']['body'])

    def test_unknown_and_required_do_not_bypass_sources(self):
        self.c.db.execute('DELETE FROM dress_rules')
        self.c.db.commit()
        for value in ['unknown', 'required']:
            self.data['events'][0]['dress_applicability'] = value
            self.c.import_calendar(self.data, now=NOW)
            self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_not_applicable_cannot_bypass_event_scope(self):
        event = self.data['events'][0]
        event.pop('attire', None)
        event.update(dress_applicability='not_applicable', event_type='outside-scope')
        self.c.import_calendar(self.data, now=NOW)
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_contradictory_or_unknown_values_are_rejected(self):
        event = self.data['events'][0]
        for value in ['not_applicable', 'ignore_rules']:
            event.update(dress_applicability=value, attire='Uniform')
            with self.assertRaises(ValueError):
                self.c.import_calendar(self.data, now=NOW)
