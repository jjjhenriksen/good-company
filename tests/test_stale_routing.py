import unittest
import test_tasks as base
from test_core import NOW
from good_company.core import stamp
from datetime import timedelta


class StaleRoutingTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def overdue(self):
        self.c.delegate(now=NOW)
        notice = next(n for n in self.c.task_queue() if n['kind'] == '24h')
        self.c.db.execute('UPDATE task_notices SET due=? WHERE id=?', ((stamp(NOW) - timedelta(hours=3)).isoformat(), notice['id']))
        self.c.db.commit()
        return notice['id']

    def test_overdue_sender_and_recipient_refresh(self):
        nid = self.overdue()
        policy = self.c.autonomy()
        policy['sender'] = 'new-sender@example.invalid'
        policy['allowed_recipients'].append('new-alex@example.invalid')
        self.c.configure_autonomy(policy, 'verified sender', now=NOW)
        v = base.volunteer()
        v['email'] = 'new-alex@example.invalid'
        self.c.set_volunteer(v, 'verified address change', now=NOW)
        with self.assertRaises(ValueError):
            self.c.task_claim(nid, now=NOW)
        self.c.delegate(now=NOW)
        message = self.c.task_claim(nid, now=NOW)['message']
        self.assertEqual(message['to'], ['new-alex@example.invalid'])
        self.assertEqual(message['sender'], 'new-sender@example.invalid')

    def test_optout_retires_pending_but_preserves_attempt(self):
        nid = self.overdue()
        self.c.task_claim(nid, now=NOW)
        before = next(n for n in self.c.task_queue() if n['id'] == nid)
        v = base.volunteer()
        v['accepts_delegation'] = False
        self.c.set_volunteer(v, 'verified stop', now=NOW)
        self.c.delegate(now=NOW)
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == nid), before)
        self.assertTrue(all(n['status'] == 'cancelled' for n in self.c.task_queue() if n['id'] != nid))
