import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from good_company.onboarding import SetupCoordinator
from good_company.migrations import migrate, VERSION


class MigrationTests(unittest.TestCase):
    def test_legacy_authority_receipts_and_identity_survive_upgrade_and_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.sqlite'
            c=SetupCoordinator(path)
            c.db.execute("INSERT INTO settings VALUES('autonomy',?)",(json.dumps({'enabled':False}),))
            c.db.execute("INSERT INTO audit(at,action,object_id,detail) VALUES('2026-09-26T00:00:00Z','send_claim','sent-once','{}')")
            c.db.execute("INSERT INTO corrections VALUES('sent-once','event','original','rev','policy','{}','sent','2026-09-26T00:00:00Z','provider-receipt','authority')")
            c.db.execute('PRAGMA user_version=0');c.db.commit();c.db.close()
            identity=Path(folder)/'install-id';identity.write_text('stable-install')
            c=SetupCoordinator(path)
            self.assertEqual(c.db.execute('PRAGMA user_version').fetchone()[0],VERSION)
            self.assertEqual(c.autonomy(),{'enabled':False})
            self.assertEqual(c.db.execute("SELECT receipt FROM corrections WHERE id='sent-once'").fetchone()[0],'provider-receipt')
            c.db.close()
            backup=next(Path(folder).glob(f'*.pre-v{VERSION}.*.sqlite'))
            # Restore only before any new work has run after migration.
            path.write_bytes(backup.read_bytes())
            c=SetupCoordinator(path)
            self.assertEqual(c.db.execute("SELECT status FROM corrections WHERE id='sent-once'").fetchone()[0],'sent')
            self.assertEqual(identity.read_text(),'stable-install');c.db.close()

    def test_failure_rolls_back_ddl_and_leaves_private_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.sqlite';db=sqlite3.connect(path)
            db.execute('CREATE TABLE preserved(value TEXT)');db.execute("INSERT INTO preserved VALUES('authority')");db.commit()
            with self.assertRaises(sqlite3.Error):
                migrate(db,path,'CREATE TABLE partial(value TEXT);\nINVALID SQL;\n')
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='partial'").fetchone())
            self.assertEqual(db.execute('SELECT * FROM preserved').fetchone()[0],'authority')
            self.assertTrue(list(Path(folder).glob(f'*.pre-v{VERSION}.*.sqlite')));db.close()

    def test_v1_upgrade_preserves_optional_unknown_send_and_blocks_old_budget_code(self):
        from unittest.mock import patch
        from good_company.modules import ModuleCoordinator
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.sqlite'
            c = ModuleCoordinator(path)
            c.db.execute("INSERT INTO module_notices VALUES('one','resources','booking',1,'policy','2026-10-01T17:00:00Z','uncertain','{}','original-provider-handle')")
            c.db.execute('PRAGMA user_version=1'); c.db.commit(); c.db.close()
            c = ModuleCoordinator(path)
            self.assertEqual(c.db.execute('SELECT receipt FROM module_notices').fetchone()[0], 'original-provider-handle')
            self.assertEqual(c.db.execute('PRAGMA user_version').fetchone()[0], 2)
            c.db.close()
            with patch('good_company.migrations.VERSION', 1), self.assertRaisesRegex(ValueError, 'newer'):
                ModuleCoordinator(path)

    def test_newer_schema_refuses_older_code(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'db';db=sqlite3.connect(path);db.execute('PRAGMA user_version=999');db.close()
            with self.assertRaises(ValueError): SetupCoordinator(path)
