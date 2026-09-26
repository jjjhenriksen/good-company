import unittest
import test_tasks as base
from test_core import NOW


class RolePredicateTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_all_requires_every_role(self):
        task = base.task('all-roles')
        task.update(eligible_roles=['adult volunteer', 'trained'], role_match='ALL')
        self.c.add_task(task, 'verified request', now=NOW)
        result = self.c.delegate(now=NOW)
        self.assertNotIn('all-roles', [a['task_id'] for a in result['assigned']])
        volunteer = base.volunteer('sam')
        volunteer['roles'].append('trained')
        self.c.set_volunteer(volunteer, 'verified roster', now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'][0]['task_id'], 'all-roles')

    def test_legacy_and_explicit_any_allow_intersection(self):
        for mode in [None, 'ANY']:
            task = base.task('any-' + str(mode))
            task['eligible_roles'] = ['adult volunteer', 'trained']
            if mode:
                task['role_match'] = mode
            self.c.add_task(task, 'verified request', now=NOW)
            self.assertTrue(self.c._eligible(base.volunteer(), task, self.c.autonomy()))

    def test_unknown_role_evidence_cannot_satisfy_all(self):
        task = base.task()
        task['role_match'] = 'ALL'
        volunteer = base.volunteer()
        volunteer['roles'] = []
        self.assertFalse(self.c._eligible(volunteer, task, self.c.autonomy()))

    def test_invalid_predicate_is_rejected(self):
        task = base.task('invalid')
        task['role_match'] = 'either'
        with self.assertRaises(ValueError):
            self.c.add_task(task, 'verified request', now=NOW)
