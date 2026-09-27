import json
import unittest
import test_tasks as base
from good_company.corrections import CorrectionCoordinator
from good_company.core import digest
from test_core import NOW


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        base.TaskTests.setUp(self)
        self.c.db.close()
        self.c = CorrectionCoordinator(base.Path(self.tmp.name) / 'tasks.sqlite')
        self.c.delegate(now=NOW)
        self.original = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.task_claim(self.original['id'], now=NOW)
        self.c.task_receipt(self.original['id'], 'sent', 'original-receipt', now=NOW)
        self.c.close_task('chairs', 'cancelled', 'verified cancellation', now=NOW)
        self.message = dict(self.original['message'], subject='Correction: task cancelled', body='The welcome-table task is cancelled.')

    tearDown = base.TaskTests.tearDown

    def create(self):
        return self.c.create_correction('task', self.original['id'], self.message, digest(self.message), 'verified cancellation', now=NOW)['id']

    def test_correction_deduplicates_and_uncertain_never_retries(self):
        cid = self.create()
        self.assertEqual(self.create(), cid)
        self.c.correction_claim(cid, now=NOW)
        self.c.correction_receipt(cid, 'uncertain', 'provider-timeout', now=NOW)
        with self.assertRaises(ValueError):
            self.c.correction_claim(cid, now=NOW)
        self.c.correction_receipt(cid, 'sent', 'reconciled-receipt', now=NOW)
        self.assertEqual(self.c.communication_budget(now=NOW)['used'], 2)
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == self.original['id'])['receipt'], 'original-receipt')

    def test_recipient_expansion_is_rejected(self):
        self.message['to'] = ['sam@example.invalid']
        with self.assertRaises(ValueError):
            self.create()

    def test_stop_before_correction_claim_blocks(self):
        cid = self.create()
        self.c.set_contact_consent('alex@example.invalid', False, 'verified stop', now=NOW)
        with self.assertRaises(ValueError):
            self.c.correction_claim(cid, now=NOW)

    def test_uncertain_original_requires_reconciliation(self):
        self.c.db.execute("UPDATE task_notices SET status='uncertain' WHERE id=?", (self.original['id'],))
        self.c.db.commit()
        with self.assertRaisesRegex(ValueError, 'Reconcile'):
            self.create()

    def cancelled_event(self):
        from test_core import snapshot, DUE
        data = snapshot()
        data['events'][0].pop('attire', None)
        data['events'][0].update(event_type='service activity', dress_applicability='not_applicable')
        self.c.import_calendar(data, now=NOW)
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        data['checked_at'] = DUE
        self.c.import_calendar(data, now=DUE)
        original = self.c.claim(rid, now=DUE)['message']
        self.c.receipt(rid, 'sent', 'event-receipt', now=DUE)
        data['events'] = []
        self.c.import_calendar(data, now=DUE)
        message = {k: original[k] for k in ('sender', 'to', 'bcc')}
        message.update(subject='Event cancelled', body='The service activity has been cancelled.')
        return rid, message

    def test_correction_cannot_expose_original_bcc_recipients(self):
        from test_core import DUE
        rid, message = self.cancelled_event()
        self.assertGreater(len(message['bcc']), 1)
        message['to'], message['bcc'] = message['bcc'], []
        with self.assertRaisesRegex(ValueError, 'hidden'):
            self.c.create_correction('event', rid, message, digest(message), 'verified cancellation', now=DUE)
        self.assertEqual(self.c.correction_queue(), [])

    def test_legacy_correction_visibility_is_rechecked_at_claim(self):
        from test_core import DUE
        rid, message = self.cancelled_event()
        cid = self.c.create_correction('event', rid, message, digest(message), 'verified cancellation', now=DUE)['id']
        message['to'], message['bcc'] = [a.upper() for a in message['bcc']], []
        with self.c.db:
            self.c.db.execute('UPDATE corrections SET message=? WHERE id=?', (json.dumps(message), cid))
        with self.assertRaisesRegex(ValueError, 'hidden'):
            self.c.correction_claim(cid, now=DUE)
        self.assertEqual(self.c.correction_queue()[0]['status'], 'pending')
        self.assertEqual(self.c.reminder(rid)['receipt'], 'event-receipt')

    def test_private_subset_correction_accepts_case_insensitive_identity(self):
        from test_core import DUE
        rid, message = self.cancelled_event()
        message['bcc'] = [message['bcc'][0].upper()]
        cid = self.c.create_correction('event', rid, message, digest(message), 'verified cancellation', now=DUE)['id']
        claim = self.c.correction_claim(cid, now=DUE)
        self.assertEqual(claim['message'], message)
        self.assertEqual(claim['message']['to'], [])

    def test_case_variant_duplicate_correction_recipients_are_rejected(self):
        self.message['bcc'] = [self.message['to'][0].upper()]
        with self.assertRaisesRegex(ValueError, 'original recipients'):
            self.create()

    def test_cancelled_event_correction_preserves_original_and_claims_once(self):
        from test_core import DUE
        rid, message = self.cancelled_event()
        cid = self.c.create_correction('event', rid, message, digest(message), 'verified calendar cancellation', now=DUE)['id']
        self.c.correction_claim(cid, now=DUE)
        with self.assertRaises(ValueError):
            self.c.correction_claim(cid, now=DUE)
        self.assertEqual(self.c.reminder(rid)['receipt'], 'event-receipt')
