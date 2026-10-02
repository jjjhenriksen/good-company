from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from module_fixture import NOW, access_request, coordinator, event_snapshot


class AccessRequestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = coordinator(Path(self.tmp.name) / 'state.sqlite', 'accessibility', 'fictional-event-service-desk')
        self.c.import_calendar(event_snapshot(), now=NOW)
        self.c.request_accessibility(access_request(), 'alex', 'verified fictional request', now=NOW)

    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()

    def update(self, action, actor='owner', evidence='fictional actual check'):
        return self.c.update_accessibility('captions', action, actor, evidence, 'verified actor reference', now=NOW)

    def status(self):
        return self.c.module_status('accessibility', 'captions', 'alex', now=NOW)

    def notice(self):
        return self.c.module_notice('accessibility', 'captions', 'alex@example.invalid', NOW.isoformat(),
                                    'owner', 'fictional notice remit', now=NOW)['id']

    def test_confirmation_and_actual_verification_are_separate(self):
        with self.assertRaises(ValueError):
            self.update('verify')
        self.update('acknowledge')
        with self.assertRaises(ValueError):
            self.update('arrange', 'owner')
        self.update('arrange', 'service', 'fictional service confirmation')
        self.assertEqual(self.status()['status'], 'arranged')
        with self.assertRaises(ValueError):
            self.update('verify', evidence='fictional service confirmation')
        self.update('verify', evidence='fictional captions tested at venue')
        self.assertEqual(self.status()['status'], 'verified')

    def test_delivery_does_not_assert_fulfillment_or_disclose_request_text(self):
        notice = self.notice()
        claim = self.c.module_claim(notice, now=NOW)
        self.assertNotIn('captions', claim['message']['body'])
        self.c.module_receipt(notice, 'sent', 'fixture-send-receipt', now=NOW)
        self.assertEqual(self.status()['status'], 'requested')

    def test_second_team_and_unconsented_recipient_cannot_access(self):
        with self.assertRaises(ValueError):
            self.c.module_status('accessibility', 'captions', 'sam', now=NOW)
        with self.assertRaises(ValueError):
            self.c.module_notice('accessibility', 'captions', 'sam@example.invalid', NOW.isoformat(),
                                 'owner', 'wrong audience', now=NOW)
        with self.assertRaises(ValueError):
            self.c.request_accessibility(access_request() | {'id': 'other', 'share_with': ['owner', 'sam']},
                                          'alex', 'invalid sharing', now=NOW)

    def test_event_change_invalidates_arrangement_and_requires_recheck(self):
        self.update('acknowledge')
        self.update('arrange', 'service', 'service confirmation')
        self.update('verify', evidence='actual check')
        notice = self.notice()
        self.c.import_calendar(event_snapshot('Different venue'), now=NOW)
        self.assertEqual(self.status()['status'], 'needs_review')
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)
        with self.assertRaises(ValueError):
            self.update('verify')
        self.update('recheck')
        self.assertEqual(self.status()['status'], 'acknowledged')
        self.assertNotIn('verification', self.status()['record'])
        self.update('arrange', 'service', 'replacement confirmation')
        self.update('verify', evidence='replacement checked')
        self.assertEqual(self.status()['status'], 'verified')

    def test_withdrawal_erases_request_and_stops_queued_notices(self):
        notice = self.notice()
        with self.assertRaises(ValueError):
            self.update('withdraw', 'owner')
        self.update('withdraw', 'alex')
        self.assertEqual(self.status()['status'], 'withdrawn')
        self.assertNotIn('arrangement', self.status()['record'])
        with self.assertRaises(ValueError):
            self.c.module_claim(notice, now=NOW)
        with self.assertRaises(ValueError):
            self.update('recheck')
        with self.assertRaises(ValueError):
            self.c.request_accessibility(access_request(), 'alex', 'replay', now=NOW)
        with self.assertRaises(ValueError):
            self.c.module_status('accessibility', 'captions', 'service', now=NOW)

    def test_missing_evidence_and_medical_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            self.update('acknowledge', evidence='')
        with self.assertRaises(ValueError):
            self.c.request_accessibility(access_request() | {'id': 'other', 'diagnosis': 'not collected'},
                                          'alex', 'invalid payload', now=NOW)

    def test_retention_removes_arrangement_and_consent_text(self):
        self.c.expire_module_records('configured retention', now=NOW + timedelta(days=31))
        self.assertEqual(self.c.db.execute("SELECT payload FROM module_records WHERE id='captions'").fetchone()[0], '{}')
