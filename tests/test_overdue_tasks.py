from datetime import timedelta
import unittest
import test_tasks as base
from test_core import NOW
from good_company.core import stamp


class OverdueTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_repeated_overdue_checks_preserve_capacity_until_verified_outcome(self):
        self.c.delegate(now=NOW)
        later = stamp(base.task()['end']) + timedelta(hours=1)
        first = self.c.overdue_tasks(now=later)
        self.assertEqual(first, self.c.overdue_tasks(now=later))
        self.assertEqual(first['overdue'][0]['task_id'], 'chairs')
        self.c.follow_up_task('chairs', 'still_open', 'verified check', 'Awaiting outcome', now=later)
        self.assertEqual(len(self.c._workload('alex')), 1)
        self.c.follow_up_task('chairs', 'completed', 'verified completion', 'Completed', now=later)
        self.assertEqual(self.c.overdue_tasks(now=later)['overdue'], [])
        self.assertEqual(self.c._workload('alex'), [])
        self.assertTrue(all(n['status'] == 'cancelled' for n in self.c.task_queue()))
