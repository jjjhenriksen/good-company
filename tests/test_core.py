import copy
import json
import tempfile
import unittest
from pathlib import Path
from good_company.core import Coordinator, digest
NOW = '2026-09-25T16:00:00+00:00'
DUE = '2026-09-26T16:00:00+00:00'
def snapshot(now=NOW):
    return {'calendar': 'demo-events-only', 'complete': True,
            'window_start': '2026-09-25T00:00:00Z', 'window_end': '2026-10-25T00:00:00Z',
            'checked_at': now, 'events': [{'id': 'dinner-instance-1', 'title': 'Community dinner',
            'start': '2026-09-27T17:30:00-07:00', 'end': '2026-09-27T19:00:00-07:00',
            'location': 'Demo hall', 'source': 'demo://calendar/event-1', 'status': 'confirmed',
            'rsvp': 'Reply by Friday for a meal headcount.'}]}
class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = Coordinator(Path(self.tmp.name) / 'test.sqlite')
        self.c.configure(json.loads(Path('examples/profile.json').read_text())['profile'])
        self.c.import_calendar(snapshot(), now=NOW)
    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()
    def draft(self):
        return self.c.plan(now=NOW)['created'][0]
    def approved(self):
        rid = self.draft(); msg = self.c.reminder(rid)['message']
        msg['to'] = ['demo@example.invalid']
        self.c.edit(rid, msg, now=NOW)
        self.c.approve(rid, digest(msg), 'demo owner message 123', now=NOW)
        return rid
    def test_retrieval_citations_and_access(self):
        self.c.ingest('# Arrival\nArrive fifteen minutes early.', 'handbook', 'Guide', NOW)
        self.c.ingest('# Private\nArrival contact private.', 'private', 'Admin', NOW, 'coordinator')
        result = self.c.retrieve('When should I arrive?', now=NOW)
        self.assertEqual(result['evidence'][0]['source'], 'handbook')
        self.assertIn('lines', result['evidence'][0]['section'])
        self.assertTrue(all(r['audience'] == 'volunteer' for r in result['evidence']))
        self.assertEqual(self.c.retrieve('unicorn spaceship', now=NOW)['evidence'], [])
    def test_reimport_and_replan_are_idempotent(self):
        self.assertEqual(len(self.c.plan(now=NOW)['created']), 1)
        self.assertEqual(self.c.import_calendar(snapshot(), now=NOW)['changes'], 0)
        self.assertEqual(self.c.plan(now=NOW)['created'], [])
    def test_changed_event_invalidates_approval(self):
        rid = self.approved(); data = snapshot(DUE)
        data['events'][0]['location'] = 'Different hall'
        self.c.import_calendar(data, now=DUE)
        self.assertEqual(self.c.reminder(rid)['status'], 'superseded')
        with self.assertRaises(ValueError): self.c.claim(rid, now=DUE)
        self.assertEqual(len(self.c.plan(now=DUE)['created']), 1)
    def test_removed_event_cancels(self):
        rid = self.approved(); data = snapshot(DUE); data['events'] = []
        self.c.import_calendar(data, now=DUE)
        self.assertEqual(self.c.reminder(rid)['status'], 'superseded')
        self.assertEqual(self.c.plan(now=DUE)['created'], [])
    def test_partial_snapshot_preserves_state(self):
        data = snapshot(); data['complete'] = False
        with self.assertRaises(ValueError): self.c.import_calendar(data, now=NOW)
        self.assertEqual(len(self.c.events()), 1)
    def test_old_snapshot_rejected(self):
        self.c.import_calendar(snapshot(DUE), now=DUE)
        with self.assertRaises(ValueError): self.c.import_calendar(snapshot(), now=DUE)
    def test_duplicate_instances_rejected_atomically(self):
        data = snapshot(); data['events'].append(copy.deepcopy(data['events'][0]))
        with self.assertRaises(ValueError): self.c.import_calendar(data, now=NOW)
        self.assertEqual(len(self.c.events()), 1)
    def test_no_send_without_recipient_or_approval(self):
        rid = self.draft()
        with self.assertRaises(ValueError): self.c.approve(rid, digest(self.c.reminder(rid)['message']), 'owner', now=NOW)
        with self.assertRaises(ValueError): self.c.claim(rid, now=DUE)
    def test_approval_binds_exact_message(self):
        rid = self.approved(); msg = self.c.reminder(rid)['message']; old = digest(msg)
        msg['body'] += '\nChanged.'; self.c.edit(rid, msg, now=NOW)
        with self.assertRaises(ValueError): self.c.approve(rid, old, 'owner', now=NOW)
        self.assertEqual(self.c.reminder(rid)['status'], 'draft')
    def test_claim_requires_fresh_calendar_and_exactly_one_send(self):
        rid = self.approved()
        with self.assertRaisesRegex(ValueError, 'Refresh'): self.c.claim(rid, now=DUE)
        self.c.import_calendar(snapshot(DUE), now=DUE)
        self.assertEqual(self.c.claim(rid, now=DUE)['id'], rid)
        with self.assertRaises(ValueError): self.c.claim(rid, now=DUE)
        self.c.receipt(rid, 'sent', 'provider-message-123', now=DUE)
        self.assertEqual(self.c.reminder(rid)['status'], 'sent')
    def test_ambiguous_send_never_automatically_retries(self):
        rid = self.approved(); self.c.import_calendar(snapshot(DUE), now=DUE)
        self.c.claim(rid, now=DUE); self.c.receipt(rid, 'uncertain', 'provider timeout', now=DUE)
        with self.assertRaises(ValueError): self.c.claim(rid, now=DUE)
    def test_all_day_time_not_invented(self):
        data = snapshot(); data['events'][0].update(all_day=True, start='2026-09-27')
        self.c.import_calendar(data, now=NOW); rid = self.draft()
        self.assertIn('event time', self.c.reminder(rid)['message']['missing'])
    def test_conflicts_hide_private_title(self):
        result = self.c.conflicts({'start': NOW, 'end': '2026-09-25T18:00:00Z'},
            [{'start': NOW, 'end': '2026-09-25T17:00:00Z', 'title': 'Secret appointment'}])
        self.assertFalse(result['available']); self.assertNotIn('Secret', json.dumps(result))
    def test_no_naive_times(self):
        data = snapshot(); data['events'][0]['start'] = '2026-09-27T17:30:00'
        with self.assertRaises(ValueError): self.c.import_calendar(data, now=NOW)
    def test_two_workers_cannot_claim_same_send(self):
        rid = self.approved(); self.c.import_calendar(snapshot(DUE), now=DUE)
        other = Coordinator(Path(self.tmp.name) / 'test.sqlite'); self.c.claim(rid, now=DUE)
        with self.assertRaises(ValueError): other.claim(rid, now=DUE)
        other.db.close()
    def test_profile_change_requires_fresh_review(self):
        rid = self.approved(); profile = self.c.profile()
        profile['signoff'] = 'New organization signoff'
        self.c.configure(profile)
        self.assertEqual(self.c.reminder(rid)['status'], 'superseded')
        self.c.plan(now=NOW)
        self.assertEqual(self.c.reminder(rid)['status'], 'draft')
        self.assertEqual(self.c.reminder(rid)['message']['to'], [])
    def test_cancelled_then_restored_event_gets_new_review(self):
        rid = self.approved(); data = snapshot(DUE); data['events'] = []
        self.c.import_calendar(data, now=DUE)
        self.c.import_calendar(snapshot(DUE), now=DUE)
        self.c.plan(now=DUE)
        self.assertEqual(self.c.reminder(rid)['status'], 'draft')
    def test_claim_before_due_is_refused(self):
        rid = self.approved()
        with self.assertRaisesRegex(ValueError, 'not due'): self.c.claim(rid, now=NOW)
    def test_state_survives_reopen(self):
        rid = self.approved(); self.c.db.close()
        self.c = Coordinator(Path(self.tmp.name) / 'test.sqlite')
        self.assertEqual(self.c.reminder(rid)['status'], 'approved')
        self.assertEqual(self.c.plan(now=NOW)['created'], [])
if __name__ == '__main__': unittest.main()
