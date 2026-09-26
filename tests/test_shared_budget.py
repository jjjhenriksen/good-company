import unittest
import test_tasks as base
from test_core import NOW
from good_company.core import stamp
from good_company.tasks import WorkCoordinator


class BudgetTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_event_attempt_consumes_task_budget_after_restart(self):
        policy = self.c.autonomy()
        policy['max_reminders_per_day'] = 1
        self.c.configure_autonomy(policy, 'owner limit', now=NOW)
        with self.c.db:
            self.c.log('send_claim', 'prior-event', {}, stamp(NOW))
        self.c.delegate(now=NOW)
        nid = next(n['id'] for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.db.close()
        self.c = WorkCoordinator(base.Path(self.tmp.name) / 'tasks.sqlite')
        with self.assertRaisesRegex(ValueError, 'shared daily'):
            self.c.task_claim(nid, now=NOW)
        self.assertEqual(self.c.communication_budget(now=NOW)['remaining'], 0)

    def test_task_attempt_consumes_budget_even_if_uncertain(self):
        policy = self.c.autonomy()
        policy['max_reminders_per_day'] = 1
        self.c.configure_autonomy(policy, 'owner limit', now=NOW)
        self.c.delegate(now=NOW)
        nid = next(n['id'] for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.task_claim(nid, now=NOW)
        self.c.task_receipt(nid, 'uncertain', 'timeout', now=NOW)
        with self.assertRaisesRegex(ValueError, 'shared daily'):
            self.c._check_communication_budget(stamp(NOW))
        self.assertEqual(self.c.communication_budget(now=NOW)['used'], 1)

    def test_concurrent_event_and_task_reservations_share_one_slot(self):
        import concurrent.futures
        import threading
        policy = self.c.autonomy()
        policy['max_reminders_per_day'] = 1
        self.c.configure_autonomy(policy, 'owner limit', now=NOW)
        barrier = threading.Barrier(2)
        path = base.Path(self.tmp.name) / 'tasks.sqlite'

        def attempt(kind):
            c = WorkCoordinator(path)
            try:
                barrier.wait(timeout=5)
                with c.db:
                    c.db.execute('BEGIN IMMEDIATE')
                    c._check_communication_budget(stamp(NOW))
                    c.log(kind, kind, {}, stamp(NOW))
                return True
            except ValueError:
                return False
            finally:
                c.db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ['send_claim', 'task_notice_claim']))
        self.assertEqual(sum(outcomes), 1)
