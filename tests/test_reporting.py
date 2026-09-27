import json
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
