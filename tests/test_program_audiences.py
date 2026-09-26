import unittest
import test_autonomy as base
from test_core import NOW, DUE


class ProgramAudienceTests(unittest.TestCase):
    setUp = base.AutonomyTests.setUp
    tearDown = base.AutonomyTests.tearDown

    def programs(self):
        self.policy['policy']['program_audiences'] = {'arts': ['alex@example.invalid'], 'food': ['sam@example.invalid']}
        self.c.configure_autonomy(**self.policy, now=NOW)

    def test_two_programs_have_disjoint_claims(self):
        self.programs()
        first = self.data['events'][0]
        first['program'] = 'arts'
        second = dict(first, id='food-event', program='food')
        self.data['events'].append(second)
        self.c.import_calendar(self.data, now=NOW)
        ids = self.c.plan(now=NOW)['automatically_authorized']
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        audiences = [self.c.claim(rid, now=DUE)['message']['bcc'] for rid in ids]
        self.assertCountEqual(audiences, [['alex@example.invalid'], ['sam@example.invalid']])

    def test_unknown_program_does_not_fall_back(self):
        self.data['events'][0]['program'] = 'unconfigured'
        self.c.import_calendar(self.data, now=NOW)
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_program_move_invalidates_old_authority(self):
        self.programs()
        self.data['events'][0]['program'] = 'arts'
        self.c.import_calendar(self.data, now=NOW)
        old = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.data['events'][0]['program'] = 'food'
        self.c.import_calendar(self.data, now=NOW)
        self.assertEqual(self.c.reminder(old)['status'], 'superseded')
        new = self.c.plan(now=NOW)['automatically_authorized'][0]
        self.assertEqual(self.c.reminder(new)['message']['bcc'], ['sam@example.invalid'])

    def test_program_cannot_expand_standing_authority(self):
        self.policy['policy']['program_audiences'] = {'arts': ['stranger@example.invalid']}
        with self.assertRaises(ValueError):
            self.c.configure_autonomy(**self.policy, now=NOW)
