import json
import unittest
import test_signups as signups
from test_core import NOW
from test_participation import ParticipationTests


class ReportingTests(ParticipationTests):
    def test_export_is_reproducible_and_corrected_without_personal_fields(self):
        request=self.request();self.c.record_participation(**request)
        a=self.c.weekly_brief('2026-09-21');b=self.c.weekly_brief('2026-09-21')
        self.assertEqual(a,b);self.assertEqual(a['programs']['food']['confirmed_minutes'],90)
        self.assertNotIn('alex',json.dumps(a));self.assertNotIn('verified-signin',json.dumps(a))
        request.update(expected_revision=1,minutes=60);self.c.record_participation(**request)
        self.assertEqual(self.c.weekly_brief('2026-09-21')['programs']['food']['confirmed_minutes'],60)

    def test_absent_outcomes_are_explicit(self):
        self.assertFalse(self.c.weekly_brief('2026-09-21')['outcome_records_supplied'])


class StaffingReportTests(unittest.TestCase):
    setUp = signups.SignupTests.setUp
    tearDown = signups.SignupTests.tearDown
    shift = signups.SignupTests.shift
    prepare = signups.SignupTests.prepare
    reply = signups.SignupTests.reply

    def test_reserved_offer_is_not_unassigned_or_confirmed(self):
        from good_company.signups import apply
        self.prepare()
        # This reporting window includes the fixture shift.
        brief = lambda: self.c.weekly_brief('2026-09-14')['upcoming']
        self.assertEqual(brief()['unassigned_tasks'], 1)
        self.assertEqual(brief()['reserved_offer_tasks'], 0)
        apply(self.c, self.reply('alex', 'signup', 'signup'), 'signup', now=NOW)
        reserved = brief()
        self.assertEqual(reserved['open_tasks'], 1)
        self.assertEqual(reserved['unassigned_tasks'], 0)
        self.assertEqual(reserved['reserved_offer_tasks'], 1)
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        apply(self.c, self.reply('alex', 'accept_offer', 'accept'), 'accept', now=NOW)
        self.assertEqual(brief()['reserved_offer_tasks'], 0)
        self.assertEqual(brief()['unassigned_tasks'], 0)
        self.assertEqual(self.c.shift_status('packing')['filled'], 1)

    def test_declined_offer_becomes_unassigned(self):
        from good_company.signups import apply
        self.prepare()
        apply(self.c, self.reply('alex', 'signup', 'signup'), 'signup', now=NOW)
        apply(self.c, self.reply('alex', 'decline_offer', 'decline'), 'decline', now=NOW)
        upcoming = self.c.weekly_brief('2026-09-14')['upcoming']
        self.assertEqual(upcoming['reserved_offer_tasks'], 0)
        self.assertEqual(upcoming['unassigned_tasks'], 1)
