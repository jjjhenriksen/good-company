import copy
import json
import unittest

import test_autonomy as base
import test_cycle as cycle_base
from test_core import NOW, DUE
from good_company.core import digest


class DuplicateRecipientTests(unittest.TestCase):
    setUp = base.AutonomyTests.setUp
    tearDown = base.AutonomyTests.tearDown

    def test_policy_rejects_duplicate_identities_without_changing_settings(self):
        before = self.c.autonomy()
        for field in ('allowed_recipients', 'reminder_recipients', 'program_audiences'):
            for duplicate in ('alex@example.invalid', 'ALEX@example.invalid'):
                with self.subTest(field=field, duplicate=duplicate):
                    policy = copy.deepcopy(before)
                    if field == 'program_audiences':
                        policy[field] = {'Fictional program': ['alex@example.invalid', duplicate]}
                    else:
                        policy[field].append(duplicate)
                    with self.assertRaisesRegex(ValueError, 'Duplicate recipient'):
                        self.c.configure_autonomy(policy, 'fixture owner', now=NOW)
                    self.assertEqual(self.c.autonomy(), before)

    def test_edit_rejects_duplicates_within_and_across_headers(self):
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        before = self.c.reminder(rid)
        for recipients in (
            {'to': [], 'bcc': ['alex@example.invalid', 'ALEX@example.invalid']},
            {'to': ['alex@example.invalid'], 'bcc': ['alex@example.invalid']},
            {'to': ['alex@example.invalid', 'alex@example.invalid'], 'bcc': []},
        ):
            with self.subTest(recipients=recipients):
                message = dict(before['message'], **recipients)
                with self.assertRaisesRegex(ValueError, 'Duplicate recipient'):
                    self.c.edit(rid, message, now=NOW)
                self.assertEqual(self.c.reminder(rid), before)

    def test_legacy_approval_fails_cleanly_before_any_claim(self):
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        item = self.c.reminder(rid)
        item['message']['bcc'].append('ALEX@example.invalid')
        with self.c.db:
            self.c.db.execute('UPDATE reminders SET message=?,approval=? WHERE id=?',
                (json.dumps(item['message']), json.dumps({'message_hash': digest(item['message']), 'authority': 'legacy fixture'}), rid))
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        with self.assertRaisesRegex(ValueError, 'Duplicate recipient'):
            self.c.claim(rid, now=DUE)
        self.assertEqual(self.c.reminder(rid)['status'], 'approved')
        self.assertEqual(self.c.db.execute('SELECT count(*) FROM communication_claims').fetchone()[0], 0)

    def test_distinct_recipient_headers_are_preserved(self):
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        message = self.c.reminder(rid)['message']
        message.update(to=['alex@example.invalid'], bcc=['sam@example.invalid'])
        self.c.edit(rid, message, now=NOW)
        self.c.approve(rid, digest(message), 'fixture owner', now=NOW)
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        self.assertEqual(self.c.claim(rid, now=DUE)['message'], message)


class DuplicateCycleTests(unittest.TestCase):
    setUp = cycle_base.CycleTests.setUp
    tearDown = cycle_base.CycleTests.tearDown
    run_cycle = cycle_base.CycleTests.run_cycle

    def test_legacy_duplicate_notice_does_not_stop_valid_assignment(self):
        self.c.import_calendar(self.window, now=NOW)
        rid = self.c.plan(now=NOW)['created'][0]
        message = self.c.reminder(rid)['message']
        message.update(to=[], bcc=['alex@example.invalid', 'ALEX@example.invalid'], missing=[])
        with self.c.db:
            self.c.db.execute("UPDATE reminders SET message=?,approval=?,status='approved',due=? WHERE id=?",
                (json.dumps(message), json.dumps({'message_hash': digest(message), 'authority': 'legacy fixture'}), NOW, rid))
        result = self.run_cycle()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['deferred'], 1)
        self.assertEqual(result['sent'], 1)
        self.assertEqual(len(self.p.sent), 1)
        self.assertEqual(self.c.reminder(rid)['status'], 'approved')
