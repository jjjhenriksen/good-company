import unittest
from unittest.mock import patch
import test_autonomy as base
from test_core import NOW, DUE


class MixedRoleTests(unittest.TestCase):
    tearDown = base.AutonomyTests.tearDown

    def setUp(self):
        base.AutonomyTests.setUp(self)
        self.policy['policy']['recipient_roles'] = {'alex@example.invalid': 'member', 'sam@example.invalid': 'adult volunteer'}
        self.c.configure_autonomy(**self.policy, now=NOW)
        self.data['events'][0].pop('attire', None)
        self.data['events'][0]['mixed_role_audience'] = True
        self.c.import_calendar(self.data, now=NOW)

    def test_role_groups_are_separate_sourced_and_deduplicated(self):
        ids = self.c.plan(now=NOW)['automatically_authorized']
        self.assertEqual(len(ids), 2)
        self.assertEqual(self.c.plan(now=NOW)['created'], [])
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        messages = [self.c.claim(rid, now=DUE)['message'] for rid in ids]
        alex = next(m for m in messages if m['bcc'] == ['alex@example.invalid'])
        sam = next(m for m in messages if m['bcc'] == ['sam@example.invalid'])
        self.assertIn('demo club shirt', alex['body'])
        self.assertNotIn('plain shirt', alex['body'])
        self.assertIn('plain shirt', sam['body'])
        self.assertNotIn('demo club shirt', sam['body'])
        self.assertTrue(all(m['sources'] for m in messages))

    def test_unknown_recipient_role_blocks_groups(self):
        del self.policy['policy']['recipient_roles']['sam@example.invalid']
        self.c.configure_autonomy(**self.policy, now=NOW)
        result = self.c.plan(now=NOW)
        self.assertEqual(result['automatically_authorized'], [])
        self.assertTrue(result['exceptions'])

    def test_private_rules_do_not_enter_group_message(self):
        import json
        from pathlib import Path
        rules = json.loads(Path('examples/dress-code.json').read_text())
        rules['rules'][1]['audience'] = 'coordinator'
        rules['rules'][1]['attire'] = 'PRIVATE-OUTFIT'
        self.c.set_dress_code(**rules, now=NOW)
        self.c.plan(now=NOW)
        self.assertNotIn('PRIVATE-OUTFIT', json.dumps(self.c.queue()))
        self.assertEqual(len([r for r in self.c.queue() if r['status'] == 'approved']), 1)

    def test_changed_role_cannot_repeat_a_previously_attempted_cadence(self):
        ids = self.c.plan(now=NOW)['automatically_authorized']
        rid = next(rid for rid in ids if self.c.reminder(rid)['message']['bcc'] == ['alex@example.invalid'])
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        self.c.claim(rid, now=DUE)
        self.c.receipt(rid, 'sent', 'fixture-role-receipt', now=DUE)
        self.policy['policy']['recipient_roles']['alex@example.invalid'] = 'adult volunteer'
        self.c.configure_autonomy(**self.policy, now=DUE)
        result = self.c.plan(now=DUE)
        self.assertEqual(result['automatically_authorized'], [])
        self.assertTrue(result['exceptions'])

    def attempt_then_change_case_and_role(self, outcome='sent', direct=False):
        ids = self.c.plan(now=NOW)['automatically_authorized']
        rid = next(rid for rid in ids if self.c.reminder(rid)['message']['bcc'] == ['alex@example.invalid'])
        if direct:
            from good_company.core import digest
            message = self.c.reminder(rid)['message']
            message.update(to=message['bcc'], bcc=[])
            self.c.edit(rid, message, now=NOW)
            self.c.approve(rid, digest(message), 'fictional owner', now=NOW)
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        self.c.claim(rid, now=DUE)
        self.c.receipt(rid, outcome, 'fixture-original-receipt', now=DUE)
        policy = self.policy['policy']
        for field in ('allowed_recipients', 'reminder_recipients'):
            policy[field] = ['ALEX@example.invalid' if a == 'alex@example.invalid' else a for a in policy[field]]
        del policy['recipient_roles']['alex@example.invalid']
        policy['recipient_roles']['ALEX@example.invalid'] = 'adult volunteer'
        self.c.configure_autonomy(**self.policy, now=DUE)
        return rid

    def test_case_and_role_change_cannot_reauthorize_attempted_recipient(self):
        original = self.attempt_then_change_case_and_role()
        before = self.c.reminder(original)
        result = self.c.plan(now=DUE)
        self.assertEqual(result['automatically_authorized'], [])
        self.assertTrue(result['exceptions'])
        self.assertEqual(self.c.reminder(original), before)

    def test_direct_original_recipient_keeps_case_insensitive_attempt_history(self):
        self.attempt_then_change_case_and_role(direct=True)
        self.assertEqual(self.c.plan(now=DUE)['automatically_authorized'], [])

    def test_legacy_queued_group_cannot_claim_after_uncertain_case_changed_attempt(self):
        original = self.attempt_then_change_case_and_role('uncertain')
        # Emulate a group queued by the old planner before the guard was fixed.
        with patch.object(self.c, '_prior_group_attempt', return_value=None):
            new = self.c.plan(now=DUE)['automatically_authorized'][0]
        before = self.c.reminder(original)
        with self.assertRaisesRegex(ValueError, 'previous revision'):
            self.c.claim(new, now=DUE)
        self.assertEqual(self.c.reminder(new)['status'], 'approved')
        self.assertEqual(self.c.reminder(original), before)

    def test_distinct_unattempted_recipient_still_receives_its_group(self):
        self.attempt_then_change_case_and_role()
        policy = self.policy['policy']
        policy['reminder_recipients'] = ['sam@example.invalid']
        self.c.configure_autonomy(**self.policy, now=DUE)
        new = self.c.plan(now=DUE)['automatically_authorized'][0]
        self.assertEqual(self.c.claim(new, now=DUE)['message']['bcc'], ['sam@example.invalid'])
