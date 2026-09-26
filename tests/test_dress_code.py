import copy
import json
import tempfile
import unittest
from pathlib import Path
from good_company.core import Coordinator, digest
from test_core import NOW, snapshot


class DressCodeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = Coordinator(Path(self.tmp.name) / 'rules.sqlite')
        self.c.configure(json.loads(Path('examples/profile.json').read_text())['profile'])
        self.rules = json.loads(Path('examples/dress-code.json').read_text())
        self.c.set_dress_code(**self.rules, now=NOW)
        self.query = {'event_type': 'service activity', 'role': 'member', 'on': '2026-09-27', 'now': NOW}

    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()

    def test_supported_answer_has_document_version_and_section(self):
        result = self.c.dress_code(**self.query)
        self.assertEqual(result['status'], 'supported')
        self.assertIn('demo club shirt', result['attire'])
        self.assertEqual(result['citations'][0]['version'], 'Fictional 2026 example')
        self.assertIn('section 2', result['citations'][0]['section'])

    def test_role_changes_the_answer(self):
        result = self.c.dress_code(**(self.query | {'role': 'adult volunteer'}))
        self.assertEqual(result['status'], 'supported')
        self.assertIn('plain shirt', result['attire'])
        self.assertNotIn('demo club shirt', result['attire'])

    def test_unknown_role_requires_question(self):
        result = self.c.dress_code(**(self.query | {'role': None}))
        self.assertEqual(result['status'], 'needs_context')
        self.assertIn('role', result['missing'])

    def test_no_invented_rules_for_another_event_type(self):
        result = self.c.dress_code(**(self.query | {'event_type': 'installation'}))
        self.assertEqual(result['status'], 'needs_source')
        self.assertNotIn('attire', result)

    def test_conflicting_sources_do_not_pick_a_winner(self):
        other = copy.deepcopy(self.rules)
        other['source'] = 'demo://other-handbook'
        other['rules'][0]['attire'] = 'A different outfit.'
        self.c.set_dress_code(**other, now=NOW)
        result = self.c.dress_code(**self.query)
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(len(result['citations']), 2)
        self.assertNotIn('attire', result)

    def test_expired_rule_is_not_used(self):
        result = self.c.dress_code(**(self.query | {'on': '2027-01-01'}))
        self.assertEqual(result['status'], 'needs_source')

    def test_review_deadline_blocks_confident_answer(self):
        self.rules['rules'][0]['review_by'] = '2026-09-20'
        self.c.set_dress_code(**self.rules, now=NOW)
        self.assertEqual(self.c.dress_code(**self.query)['status'], 'needs_review')

    def test_private_rule_does_not_leak(self):
        self.rules['rules'][0]['audience'] = 'coordinator'
        self.c.set_dress_code(**self.rules, now=NOW)
        self.assertEqual(self.c.dress_code(**self.query)['status'], 'needs_source')
        self.assertEqual(self.c.dress_code(**(self.query | {'audience': 'coordinator'}))['status'], 'supported')

    def test_event_note_cannot_override_rules(self):
        data = snapshot()
        data['events'][0].update(event_type='service activity', attire='Anything you like.')
        self.c.import_calendar(data, now=NOW)
        event_id = self.c.events()[0]['id']
        result = self.c.dress_code(event_id=event_id, role='member', now=NOW)
        self.assertEqual(result['status'], 'needs_review')

    def test_cancelled_event_does_not_get_an_outfit(self):
        data = snapshot(); data['events'][0]['status'] = 'cancelled'
        self.c.import_calendar(data, now=NOW)
        result = self.c.dress_code(event_id=self.c.events()[0]['id'], role='member', now=NOW)
        self.assertEqual(result['status'], 'cancelled')

    def test_reminder_uses_supported_attire_and_citation(self):
        data = snapshot(); data['events'][0].update(event_type='service activity', dress_code_role='member')
        self.c.import_calendar(data, now=NOW)
        rid = self.c.plan(now=NOW)['created'][0]
        message = self.c.reminder(rid)['message']
        self.assertIn('demo club shirt', message['body'])
        self.assertTrue(any('section 2' in source for source in message['sources']))
        self.assertEqual(message['missing'], [])

    def test_reminder_missing_role_blocks_approval(self):
        data = snapshot(); data['events'][0]['event_type'] = 'service activity'
        self.c.import_calendar(data, now=NOW)
        rid = self.c.plan(now=NOW)['created'][0]
        message = self.c.reminder(rid)['message']; message['to'] = ['test@example.invalid']
        self.c.edit(rid, message, now=NOW)
        with self.assertRaises(ValueError): self.c.approve(rid, digest(message), 'owner', now=NOW)

    def test_changed_rules_invalidate_approvals_but_identical_import_does_not(self):
        self.c.import_calendar(snapshot(), now=NOW)
        rid = self.c.plan(now=NOW)['created'][0]
        message = self.c.reminder(rid)['message']; message['to'] = ['test@example.invalid']
        self.c.edit(rid, message, now=NOW)
        self.c.approve(rid, digest(message), 'owner', now=NOW)
        self.assertFalse(self.c.set_dress_code(**self.rules, now=NOW)['changed'])
        self.assertEqual(self.c.reminder(rid)['status'], 'approved')
        self.rules['rules'][0]['attire'] = 'A newly documented outfit.'
        self.c.set_dress_code(**self.rules, now=NOW)
        self.assertEqual(self.c.reminder(rid)['status'], 'superseded')

    def test_source_withdrawal_removes_rules(self):
        self.c.set_dress_code(self.rules['source'], [], 'withdrawal', now=NOW)
        self.assertEqual(self.c.dress_code(**self.query)['status'], 'needs_source')

    def test_bad_source_update_preserves_previous_rules(self):
        self.rules['rules'].append(copy.deepcopy(self.rules['rules'][0]))
        with self.assertRaises(ValueError): self.c.set_dress_code(**self.rules, now=NOW)
        self.assertEqual(self.c.dress_code(**self.query)['status'], 'supported')
