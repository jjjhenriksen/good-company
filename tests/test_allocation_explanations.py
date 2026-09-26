from test_tasks import TaskTests, task
from test_core import NOW


class AllocationExplanationTests(TaskTests):
    def test_equal_fit_nonoverlapping_work_is_distributed_and_explained(self):
        self.c.close_task('chairs','cancelled','fixture',now=NOW)
        for index in range(4):
            t=task(str(index));t['preferred_skills']=[]
            t['start']=f'2026-09-27T{10+index:02}:00:00Z';t['end']=f'2026-09-27T{10+index:02}:30:00Z'
            self.c.add_task(t,'fixture',now=NOW)
        self.c.delegate(now=NOW)
        result=self.c.allocation_report()
        self.assertEqual(result['distribution']['minimum'],2)
        self.assertEqual(result['distribution']['maximum'],2)
        self.assertEqual(len(result['decisions']),4)
        self.assertTrue(all(d['selection']['eligible_candidates']>=1 for d in result['decisions']))
        self.assertEqual(result['decisions'][0]['selection']['open_work_before'],0)
