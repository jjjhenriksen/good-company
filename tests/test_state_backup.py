import json
from pathlib import Path
import tempfile
import unittest
import test_tasks as base
from test_core import NOW
from good_company.state_backup import backup_state, restore_state
from good_company.tasks import WorkCoordinator


class BackupTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_restore_preserves_identity_policy_and_deduplication(self):
        self.c.delegate(now=NOW)
        nid = next(n['id'] for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.task_claim(nid, now=NOW)
        self.c.task_receipt(nid, 'sent', 'fixture-receipt', now=NOW)
        source = Path(self.tmp.name)
        (source / 'install-id').write_text('fictional-install-identity')
        policy = self.c.autonomy()
        with tempfile.TemporaryDirectory() as area:
            backup, restored = Path(area) / 'backup', Path(area) / 'restored'
            backup_state(source, backup, offline=True)
            restore_state(backup, restored, offline=True)
            self.assertEqual((restored / 'install-id').read_text(), 'fictional-install-identity')
            self.assertEqual((backup / 'tasks.sqlite').stat().st_mode & 0o777, 0o600)
            c = WorkCoordinator(restored / 'tasks.sqlite')
            try:
                self.assertEqual(c.autonomy(), policy)
                with self.assertRaises(ValueError):
                    c.task_claim(nid, now=NOW)
                c.delegate(now=NOW)
                self.assertEqual(next(n for n in c.task_queue() if n['id'] == nid)['receipt'], 'fixture-receipt')
            finally:
                c.db.close()

    def test_corrupt_backup_does_not_create_restored_state(self):
        with tempfile.TemporaryDirectory() as area:
            backup, restored = Path(area) / 'backup', Path(area) / 'restored'
            backup_state(self.tmp.name, backup, offline=True)
            (backup / 'tasks.sqlite').write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                restore_state(backup, restored, offline=True)
            self.assertFalse(restored.exists())

    def test_overwrite_and_live_backup_are_refused(self):
        with self.assertRaises(ValueError):
            backup_state(self.tmp.name, self.tmp.name)
        with self.assertRaises(ValueError):
            backup_state(self.tmp.name, self.tmp.name, offline=True)
