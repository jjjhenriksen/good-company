import copy
import json
import tempfile
import unittest
from pathlib import Path
from good_company.tasks import WorkCoordinator
from test_core import NOW


def volunteer(vid='alex', skills=None):
    return {'id': vid, 'name': vid.title(), 'email': vid+'@example.invalid',
            'roles': ['adult volunteer'], 'skills': skills or {'organizing': 3, 'writing': 1},
            'accepts_delegation': True, 'max_open_tasks': 2,
            'avoid_categories': [], 'preferred_categories': ['event preparation'],
            'availability': [{'start':'2026-09-25T00:00:00Z','end':'2026-10-01T00:00:00Z'}]}


def task(tid='chairs'):
    return {'id': tid, 'title':'Prepare the welcome table', 'category':'event preparation',
            'start':'2026-09-27T17:00:00-07:00', 'end':'2026-09-27T17:30:00-07:00',
            'eligible_roles':['adult volunteer'], 'required_skills':{'organizing':2},
            'preferred_skills':['organizing']}


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.c=WorkCoordinator(Path(self.tmp.name)/'tasks.sqlite')
        self.c.configure(json.loads(Path('examples/profile.json').read_text())['profile'])
        self.c.configure_autonomy(**json.loads(Path('examples/autonomy.json').read_text()),now=NOW)
        for v in [volunteer(), volunteer('sam',{'organizing':2,'writing':3})]:
            self.c.set_volunteer(v,'fictional roster',now=NOW)
        self.c.add_task(task(),'fictional todo list',now=NOW)
    def tearDown(self):
        self.c.db.close(); self.tmp.cleanup()
    def test_assigns_to_stated_strength_and_queues_notice(self):
        result=self.c.delegate(now=NOW)
        self.assertEqual(result['assigned'][0]['volunteer_id'],'alex')
        self.assertEqual(result['assigned'][0]['delivery'],'queued, not yet sent')
        self.assertEqual(len(self.c.task_queue()),3)
    def test_no_repeated_assignment_or_messages(self):
        self.c.delegate(now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'],[])
        self.assertEqual(len(self.c.task_queue()),3)
    def test_unavailable_volunteer_is_skipped(self):
        v=volunteer(); v['availability']=[]
        self.c.set_volunteer(v,'updated availability',now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'][0]['volunteer_id'],'sam')
    def test_role_constraint_is_hard(self):
        v=volunteer(); v['roles']=['guest']
        self.c.set_volunteer(v,'roles',now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'][0]['volunteer_id'],'sam')
    def test_preference_to_avoid_task_is_respected(self):
        v=volunteer(); v['avoid_categories']=['event preparation']
        self.c.set_volunteer(v,'preference',now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'][0]['volunteer_id'],'sam')
    def test_overlapping_tasks_are_distributed(self):
        self.c.add_task(task('other'),'todo list',now=NOW)
        result=self.c.delegate(now=NOW)
        self.assertEqual({x['volunteer_id'] for x in result['assigned']},{'alex','sam'})
    def test_decline_reassigns_without_guardian_approval(self):
        original=self.c.delegate(now=NOW)['assigned'][0]
        self.c.decline_task(original['assignment_id'],'alex','verified response',now=NOW)
        result=self.c.delegate(now=NOW)
        self.assertEqual(result['assigned'][0]['volunteer_id'],'sam')
    def test_notice_claims_once_and_does_not_expose_skill_scores(self):
        self.c.delegate(now=NOW)
        notice=next(n for n in self.c.task_queue() if n['kind']=='assignment')
        claim=self.c.task_claim(notice['id'],now=NOW)
        self.assertNotIn('skills',claim['message']['body'])
        with self.assertRaises(ValueError): self.c.task_claim(notice['id'],now=NOW)
        self.c.task_receipt(notice['id'],'sent','demo provider receipt',now=NOW)
    def test_no_capacity_returns_exception(self):
        for vid in ['alex','sam']:
            v=volunteer(vid); v['accepts_delegation']=False
            self.c.set_volunteer(v,'preference',now=NOW)
        result=self.c.delegate(now=NOW)
        self.assertEqual(result['assigned'],[])
        self.assertEqual(len(result['exceptions']),1)
    def test_done_task_cancels_queued_reminders(self):
        self.c.delegate(now=NOW)
        self.c.close_task('chairs','completed','completion receipt',now=NOW)
        self.assertTrue(all(n['status']=='cancelled' for n in self.c.task_queue()))
    def test_changed_roster_blocks_pending_send(self):
        self.c.delegate(now=NOW)
        notice=next(n for n in self.c.task_queue() if n['kind']=='assignment')
        v=volunteer();v['accepts_delegation']=False
        self.c.set_volunteer(v,'opt out',now=NOW)
        with self.assertRaises(ValueError): self.c.task_claim(notice['id'],now=NOW)
