import unittest
import test_tasks as base
from test_core import NOW, snapshot


class LinkedTaskTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def link(self):
        self.data = snapshot()
        self.c.import_calendar(self.data, now=NOW)
        self.c.close_task('chairs', 'cancelled', 'fixture', now=NOW)
        t = base.task('linked')
        t['event_id'] = self.c.events()[0]['id']
        self.c.add_task(t, 'verified task source', now=NOW)

    def test_change_before_assignment_yields_impact_and_no_assignment(self):
        self.link()
        self.data['events'][0]['location'] = 'Changed venue'
        result = self.c.import_calendar(self.data, now=NOW)
        self.assertEqual(result['impacts'][0]['reason'], 'event_changed')
        self.assertEqual(self.c.delegate(now=NOW)['assigned'], [])

    def test_cancel_after_attempt_preserves_history_and_blocks_pending(self):
        self.link()
        self.c.delegate(now=NOW)
        nid = next(n['id'] for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.task_claim(nid, now=NOW)
        self.c.task_receipt(nid, 'sent', 'fixture-provider-receipt', now=NOW)
        self.data['events'] = []
        self.c.import_calendar(self.data, now=NOW)
        impact = self.c.task_impacts()['impacts'][0]
        self.assertEqual(impact['reason'], 'event_cancelled')
        self.assertEqual(impact['attempts'][0]['receipt'], 'fixture-provider-receipt')
        self.assertTrue(all(n['status'] == 'cancelled' for n in self.c.task_queue() if n['id'] != nid))

    def test_unknown_event_cannot_be_linked(self):
        t = base.task('unknown-link')
        t['event_id'] = 'unknown'
        with self.assertRaises(ValueError):
            self.c.add_task(t, 'task request', now=NOW)
