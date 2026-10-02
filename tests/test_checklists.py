from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from module_fixture import NOW, checklist, coordinator, event_snapshot
from good_company.core import digest


class ChecklistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = coordinator(Path(self.tmp.name) / 'state.sqlite', 'checklists', 'fictional-document-register')
        self.c.add_checklist(checklist(), 'owner', 'fictional authoritative requirements', now=NOW)

    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()

    def update(self, action, actor='owner', **kwargs):
        return self.c.update_checklist('consent-form', action, actor, 'fictional actual source observation',
                                       'verified actor', now=NOW, **kwargs)

    def status(self):
        return self.c.module_status('checklists', 'consent-form', 'alex', now=NOW)

    def test_reported_submission_is_not_acknowledgment_or_compliance(self):
        self.update('report-submitted', 'alex')
        self.assertEqual(self.status()['status'], 'reported_submitted')
        with self.assertRaises(ValueError):
            self.update('acknowledge', 'alex')
        self.update('acknowledge')
        self.assertEqual(self.status()['status'], 'acknowledged')
        self.assertNotIn('compliant', str(self.status()))

    def test_queued_reminder_and_receipt_never_mark_item_submitted(self):
        notices = self.c.plan_module_notices(now=NOW)['queued']
        self.assertEqual(len(notices), 1)
        notice = notices[0]
        claim = self.c.module_claim(notice, now=NOW)
        self.assertIn('2026-10-02', claim['message']['body'])
        self.assertIn('does not certify compliance', claim['message']['body'])
        self.c.module_receipt(notice, 'sent', 'fictional-provider-receipt', now=NOW)
        self.assertEqual(self.status()['status'], 'missing')
        self.assertEqual(self.c.plan_module_notices(now=NOW + timedelta(minutes=2))['queued'], [])

    def test_changed_deadline_and_version_invalidate_pending_reminder(self):
        notice = self.c.plan_module_notices(now=NOW)['queued'][0]
        self.update('change-deadline', due='2026-10-04T16:00:00Z')
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)
        self.assertEqual(self.c.plan_module_notices(now=NOW)['queued'], [])
        self.update('acknowledge')
        self.update('replace-version', form_version='v2')
        self.assertEqual(self.status()['status'], 'missing')
        self.assertNotIn('acknowledgment', self.status()['record'])

    def test_acknowledgment_and_withdrawal_stop_pending_reminders(self):
        notice = self.c.plan_module_notices(now=NOW)['queued'][0]
        self.update('acknowledge')
        self.assertEqual(self.c.plan_module_notices(now=NOW)['queued'], [])
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)
        self.update('withdraw', 'alex')
        self.assertNotIn('title', self.status()['record'])
        with self.assertRaises(ValueError):
            self.update('mark-missing')

    def test_other_participant_and_wrong_source_have_no_authority(self):
        with self.assertRaises(ValueError):
            self.c.module_status('checklists', 'consent-form', 'sam', now=NOW)
        with self.assertRaises(ValueError):
            self.update('report-submitted', 'sam')
        with self.assertRaises(ValueError):
            self.c.add_checklist(checklist() | {'id': 'other', 'source': 'unapproved-register'}, 'owner', 'invalid', now=NOW)

    def test_missing_deadline_consent_or_contents_are_rejected(self):
        for change in ({'due': None}, {'consent': ''}, {'contents': 'not stored'}, {'due': '2026-10-02'},
                       {'form_url': 'https://username:password@example.invalid/form'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.c.add_checklist(checklist() | {'id': 'other'} | change, 'owner', 'invalid', now=NOW)

    def test_retention_erases_item_and_notice_content(self):
        self.c.plan_module_notices(now=NOW)
        self.c.expire_module_records('retention', now=NOW + timedelta(days=31))
        self.assertEqual(self.c.db.execute("SELECT payload FROM module_records WHERE id='consent-form'").fetchone()[0], '{}')
        self.assertEqual(self.c.module_queue()[0]['message']['body'], '[expired]')

    def test_changed_event_requires_owner_rechecking_and_new_status_evidence(self):
        self.c.import_calendar(event_snapshot(), now=NOW)
        self.c.add_checklist(checklist() | {'id': 'linked', 'event_id': digest(['demo-events-only', 'event-one'])[:24]},
                             'owner', 'event requirement', now=NOW)
        self.c.import_calendar(event_snapshot('Moved event'), now=NOW)
        self.assertEqual(self.c.module_status('checklists', 'linked', 'alex', now=NOW)['status'], 'needs_review')
        with self.assertRaises(ValueError):
            self.c.update_checklist('linked', 'acknowledge', 'owner', 'old evidence', 'owner', now=NOW)
        result = self.c.update_checklist('linked', 'recheck-event', 'owner', 'current requirement confirmed', 'owner', now=NOW)
        self.assertEqual(result['status'], 'missing')

    def test_repeated_source_update_keeps_revision_and_notice_identity(self):
        first = self.update('change-deadline', due='2026-10-02T18:00:00Z')
        second = self.update('change-deadline', due='2026-10-02T18:00:00Z')
        self.assertTrue(second['replayed'])
        self.assertEqual(first['revision'], second['revision'])
