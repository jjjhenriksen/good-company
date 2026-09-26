import unittest
from pathlib import Path
import test_tasks as base
from test_core import NOW
from good_company.tasks import WorkCoordinator


class BeforeLock:
    """Deterministically commit another connection's update before BEGIN."""
    def __init__(self, connection, callback):
        self.connection, self.callback = connection, callback
    def __getattr__(self, name):
        return getattr(self.connection, name)
    def __enter__(self):
        self.connection.__enter__()
        return self
    def __exit__(self, *args):
        return self.connection.__exit__(*args)
    def execute(self, sql, *args):
        if sql == 'BEGIN IMMEDIATE' and self.callback:
            callback, self.callback = self.callback, None
            callback()
        return self.connection.execute(sql, *args)


class TaskPolicyTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_removed_cadence_is_cancelled_after_delegate(self):
        self.c.delegate(now=NOW)
        old = next(n for n in self.c.task_queue() if n['kind'] == '24h')
        policy = self.c.autonomy(); policy['task_reminder_hours'] = [2]
        self.c.configure_autonomy(policy, 'changed cadence', now=NOW)
        self.c.delegate(now=NOW)
        with self.assertRaises(ValueError): self.c.task_claim(old['id'], now=old['due'])
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == old['id'])['status'], 'cancelled')
        self.assertEqual(next(n for n in self.c.task_queue() if n['kind'] == '2h')['status'], 'pending')

    def test_claim_defends_even_if_old_notice_survives_reconciliation(self):
        self.c.delegate(now=NOW)
        old = next(n for n in self.c.task_queue() if n['kind'] == '24h')
        policy = self.c.autonomy(); policy['task_reminder_hours'] = []
        self.c.configure_autonomy(policy, 'disabled reminders', now=NOW)
        self.c.delegate(now=NOW)
        # Migration fixture: an older queue record survived policy reconciliation.
        with self.c.db:
            self.c.db.execute("UPDATE task_notices SET status='pending' WHERE id=?", (old['id'],))
        with self.assertRaisesRegex(ValueError, 'cadence'):
            self.c.task_claim(old['id'], now=old['due'])

    def test_reenable_cadence_preserves_sent_and_revives_only_unsent(self):
        self.c.delegate(now=NOW)
        assignment = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.task_claim(assignment['id'], now=NOW)
        self.c.task_receipt(assignment['id'], 'sent', 'fixture-only', now=NOW)
        policy = self.c.autonomy(); original = list(policy['task_reminder_hours'])
        policy['task_reminder_hours'] = []
        self.c.configure_autonomy(policy, 'pause reminders', now=NOW); self.c.delegate(now=NOW)
        policy['task_reminder_hours'] = original
        self.c.configure_autonomy(policy, 'resume reminders', now=NOW); self.c.delegate(now=NOW)
        self.assertEqual([n['status'] for n in self.c.task_queue() if n['kind']=='assignment'], ['sent'])
        self.assertTrue(all(n['status']=='pending' for n in self.c.task_queue() if n['kind']!='assignment'))

    def pause_at_lock(self):
        other = WorkCoordinator(Path(self.tmp.name)/'tasks.sqlite')
        def pause():
            policy = other.autonomy(); policy['enabled'] = False
            other.configure_autonomy(policy, 'owner pause', now=NOW)
        self.c.db = BeforeLock(self.c.db, pause)
        self.addCleanup(other.db.close)

    def test_pause_committed_before_claim_lock_is_honored(self):
        self.c.delegate(now=NOW)
        notice = next(n for n in self.c.task_queue() if n['kind']=='assignment')
        self.pause_at_lock()
        with self.assertRaisesRegex(ValueError, 'paused'):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(next(n for n in self.c.task_queue() if n['id']==notice['id'])['status'], 'pending')

    def test_pause_committed_before_delegate_lock_is_honored(self):
        self.pause_at_lock()
        self.assertEqual(self.c.delegate(now=NOW)['assigned'], [])
        self.assertEqual(self.c.task_queue(), [])

    def test_sender_change_refreshes_unsent_notices(self):
        self.c.delegate(now=NOW)
        notice = next(n for n in self.c.task_queue() if n['kind']=='assignment')
        policy = self.c.autonomy(); policy['sender']='new@example.invalid'
        self.c.configure_autonomy(policy, 'new sender', now=NOW)
        self.c.delegate(now=NOW)
        claim=self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(claim['message']['sender'], 'new@example.invalid')
