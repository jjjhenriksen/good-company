from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import unittest
from test_tasks import TaskTests, task
from test_core import NOW
from good_company.tasks import WorkCoordinator


class ShiftTests(TaskTests):
    def shift(self):
        a,b=task('one'),task('two')
        return {'id':'packing','title':'Packing shift','capacity':2,'slots':[a,b]}

    def test_simultaneous_allocation_cannot_overbook_and_repeats_are_idempotent(self):
        self.c.close_task('chairs','cancelled','fixture',now=NOW)
        self.c.add_shift(self.shift(),'fixture',now=NOW)
        path=Path(self.tmp.name)/'tasks.sqlite'
        def allocate(_):
            c=WorkCoordinator(path)
            try:return c.delegate(now=NOW)
            finally:c.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(allocate,range(2)))
        result=self.c.shift_status('packing')
        self.assertEqual(result['filled'],2);self.assertEqual(result['unfilled'],0)
        self.c.add_shift(self.shift(),'same fixture',now=NOW)
        self.assertEqual(self.c.shift_status('packing')['filled'],2)

    def test_invalid_slot_rolls_back_whole_shift_and_missing_credential_stays_unfilled(self):
        shift=self.shift();shift['slots'][1]['required_skills']={'packing':99}
        with self.assertRaises(ValueError):self.c.add_shift(shift,'fixture',now=NOW)
        self.assertIsNone(self.c.db.execute("SELECT 1 FROM tasks WHERE id='packing:one'").fetchone())
        shift=self.shift()
        for slot in shift['slots']:slot['required_credentials']=['food-handling']
        self.c.add_shift(shift,'fixture',now=NOW);self.c.delegate(now=NOW)
        self.assertEqual(self.c.shift_status('packing')['unfilled'],2)
