import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_tasks as base
from test_core import NOW
from good_company.state_backup import backup_state, restore_state, verify_backup
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
                verify_backup(backup)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                restore_state(backup, restored, offline=True)
            self.assertFalse(restored.exists())

    def test_overwrite_and_live_backup_are_refused(self):
        with self.assertRaises(ValueError):
            backup_state(self.tmp.name, self.tmp.name)
        with self.assertRaises(ValueError):
            backup_state(self.tmp.name, self.tmp.name, offline=True)

    def test_nested_empty_directories_round_trip_privately(self):
        source = Path(self.tmp.name)
        (source / 'empty' / 'nested').mkdir(parents=True)
        (source / 'populated' / 'empty').mkdir(parents=True)
        (source / 'populated' / 'data.txt').write_text('fixture')
        with tempfile.TemporaryDirectory() as area:
            backup, restored = Path(area) / 'backup', Path(area) / 'restored'
            backup_state(source, backup, offline=True)
            restore_state(backup, restored, offline=True)
            for name in ('empty', 'empty/nested', 'populated', 'populated/empty'):
                self.assertTrue((restored / name).is_dir(), name)
                self.assertEqual((restored / name).stat().st_mode & 0o777, 0o700)
            self.assertEqual((restored / 'populated/data.txt').read_text(), 'fixture')

    def test_format_one_backups_remain_restorable(self):
        with tempfile.TemporaryDirectory() as area:
            backup, restored = Path(area) / 'backup', Path(area) / 'restored'
            backup_state(self.tmp.name, backup, offline=True)
            record = backup / 'backup-manifest.json'
            manifest = json.loads(record.read_text())
            manifest['format'] = 1
            manifest.pop('directories', None)
            record.write_text(json.dumps(manifest))
            self.assertEqual(verify_backup(backup), {
                'verified': True, 'format': 1, 'files': len(manifest['files']), 'directories': 0,
            })
            restore_state(backup, restored, offline=True)
            self.assertTrue((restored / 'tasks.sqlite').is_file())

    def test_unsafe_directory_records_refused_before_restore(self):
        for name in ('../outside', '/outside', '.', 'tasks.sqlite'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as area:
                backup, restored = Path(area) / 'backup', Path(area) / 'restored'
                backup_state(self.tmp.name, backup, offline=True)
                record = backup / 'backup-manifest.json'
                manifest = json.loads(record.read_text())
                manifest.update(format=2, directories=[name])
                record.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    verify_backup(backup)
                with self.assertRaises(ValueError):
                    restore_state(backup, restored, offline=True)
                self.assertFalse(restored.exists())

    def test_verification_cli_is_read_only_and_reports_counts_without_private_names(self):
        (Path(self.tmp.name) / 'empty' / 'nested').mkdir(parents=True)
        with tempfile.TemporaryDirectory() as area:
            backup = Path(area) / 'backup'
            backup_state(self.tmp.name, backup, offline=True)
            before = {str(p.relative_to(area)): p.read_bytes() if p.is_file() else None
                      for p in Path(area).rglob('*')}
            result = subprocess.run([sys.executable, '-m', 'good_company.state_backup', str(backup)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((backup / 'backup-manifest.json').read_text())
            self.assertEqual(json.loads(result.stdout), {
                'verified': True, 'format': 2, 'files': len(manifest['files']), 'directories': 2,
            })
            self.assertEqual(result.stderr, '')
            self.assertEqual(before, {str(p.relative_to(area)): p.read_bytes() if p.is_file() else None
                                     for p in Path(area).rglob('*')})

    def test_failed_verification_does_not_create_restore_parent(self):
        with tempfile.TemporaryDirectory() as area:
            backup = Path(area) / 'backup'
            backup_state(self.tmp.name, backup, offline=True)
            (backup / 'tasks.sqlite').write_bytes(b'corrupted')
            parent = Path(area) / 'not-created'
            with self.assertRaisesRegex(ValueError, 'checksum'):
                restore_state(backup, parent / 'state', offline=True)
            self.assertFalse(parent.exists())

    def test_invalid_manifest_cli_has_actionable_error_and_no_success_report(self):
        for value in ([], {'format': 2, 'files': {}, 'directories': [], 'modes': []}):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as area:
                (Path(area) / 'backup-manifest.json').write_text(json.dumps(value))
                result = subprocess.run([sys.executable, '-m', 'good_company.state_backup', area],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
                self.assertIn('Unsupported backup manifest', result.stderr)
