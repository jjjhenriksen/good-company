import json
from test_tasks import TaskTests
from test_core import NOW


class ParticipationTests(TaskTests):
    def request(self):
        return dict(activity_id='packing-1',participant_id='alex',program='food',on='2026-09-26',status='confirmed',attended=True,minutes=90,source='verified-signin:1',authority='coordinator review',now=NOW)

    def test_correction_retains_original_and_requires_current_revision(self):
        result=self.c.record_participation(**self.request())
        request=self.request();request.update(minutes=60,expected_revision=1)
        self.c.record_participation(**request)
        with self.assertRaises(ValueError):self.c.record_participation(**request)
        history=self.c.participation_history(result['record_id'])['revisions']
        self.assertEqual(history[0]['current']['minutes'],90)
        self.assertEqual(history[1]['current']['minutes'],60)

    def test_missing_disputed_and_notices_never_become_hours(self):
        self.c.delegate(now=NOW)
        self.assertEqual(self.c.db.execute("SELECT count(*) FROM settings WHERE key LIKE 'participation:%'").fetchone()[0],0)
        request=self.request();request.update(status='disputed',attended=None,minutes=None)
        self.c.record_participation(**request)
        request.update(expected_revision=1,minutes=90)
        with self.assertRaises(ValueError):self.c.record_participation(**request)
