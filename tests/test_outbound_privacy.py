import copy
import json
import unittest
from pathlib import Path
import test_autonomy as autonomy
from test_core import NOW, DUE
from good_company.core import digest


class OutboundPrivacyTests(unittest.TestCase):
    setUp = autonomy.AutonomyTests.setUp
    tearDown = autonomy.AutonomyTests.tearDown

    def test_private_only_rule_blocks_automatic_reminder_without_leaking(self):
        rules = json.loads(Path('examples/dress-code.json').read_text())
        rules['source'] = 'private://coordinator-source'
        rules['rules'][0].update(audience='coordinator', attire='CONFIDENTIAL MARKER')
        self.c.set_dress_code('demo://fictional-club-dress-code', [], 'withdraw', now=NOW)
        self.c.set_dress_code(**rules, now=NOW)
        result = self.c.plan(now=NOW)
        self.assertEqual(result['automatically_authorized'], [])
        message = self.c.reminder(result['created'][0])['message']
        self.assertNotIn('CONFIDENTIAL', json.dumps(message))
        self.assertNotIn('private://', json.dumps(message))
        self.assertIn('dress code: needs_source', message['missing'])

    def test_private_rule_does_not_contaminate_public_rule_reminder(self):
        private = json.loads(Path('examples/dress-code.json').read_text())
        private['source'] = 'private://coordinator-source'
        for rule in private['rules']:
            rule.update(audience='coordinator', attire='CONFIDENTIAL MARKER')
        self.c.set_dress_code(**private, now=NOW)
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        message = self.c.reminder(rid)['message']
        self.assertIn('demo club shirt', message['body'])
        self.assertNotIn('private://', json.dumps(message))
        self.assertNotIn('CONFIDENTIAL', json.dumps(message))

    def old_template(self):
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        row = self.c.reminder(rid)
        msg = copy.deepcopy(row['message']); msg['body'] += '\nPRIVATE LEGACY TEXT'
        approval = json.loads(row['approval']); approval['message_hash'] = digest(msg)
        with self.c.db:
            self.c.db.execute('UPDATE reminders SET message=?,approval=? WHERE id=?',
                              (json.dumps(msg), json.dumps(approval), rid))
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        return rid

    def test_old_automatic_approval_cannot_send_before_replanning(self):
        rid = self.old_template()
        with self.assertRaisesRegex(ValueError, 'safe current template'):
            self.c.claim(rid, now=DUE)
        self.assertEqual(self.c.reminder(rid)['status'], 'approved')

    def test_replan_refreshes_legacy_automatic_template(self):
        rid = self.old_template()
        self.c.plan(now=DUE)
        claim = self.c.claim(rid, now=DUE)
        self.assertNotIn('PRIVATE LEGACY TEXT', claim['message']['body'])
