import unittest
import test_tasks as base
from test_core import NOW


class CredentialTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def qualified(self):
        v = base.volunteer()
        v['credentials'] = [{'name': 'food safety', 'issuer': 'Fictional training body',
                             'evidence': 'private://verified-roster', 'valid_from': '2026-01-01T00:00:00Z',
                             'valid_until': '2027-01-01T00:00:00Z', 'categories': ['event preparation']}]
        return v

    def required_task(self):
        t = base.task('qualified-task')
        t['required_credentials'] = ['food safety']
        self.c.add_task(t, 'owner requirement', now=NOW)
        return t

    def test_unknown_evidence_blocks_with_specific_exception(self):
        self.required_task()
        result = self.c.delegate(now=NOW)
        self.assertIn('credential', next(e['reason'] for e in result['exceptions'] if e['task_id'] == 'qualified-task'))

    def test_qualification_must_cover_whole_task_and_category(self):
        t = self.required_task()
        v = self.qualified()
        self.assertTrue(self.c._eligible(v, t, self.c.autonomy()))
        v['credentials'][0]['valid_until'] = t['start']
        self.assertFalse(self.c._eligible(v, t, self.c.autonomy()))
        v = self.qualified()
        v['credentials'][0]['categories'] = ['unrelated']
        self.assertFalse(self.c._eligible(v, t, self.c.autonomy()))

    def test_revocation_blocks_notice_claim(self):
        self.c.close_task('chairs', 'cancelled', 'fixture setup', now=NOW)
        self.required_task()
        self.c.set_volunteer(self.qualified(), 'verified credential evidence', now=NOW)
        self.c.delegate(now=NOW)
        notice = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.set_volunteer(base.volunteer(), 'credential revoked', now=NOW)
        with self.assertRaises(ValueError):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertNotIn('private://', notice['message']['body'])
