import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('runtime_start', Path(__file__).parents[1] / 'scripts/start_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeMigrationGuardTests(unittest.TestCase):
    def test_old_ledger_cannot_be_silently_replaced_with_empty_state(self):
        with tempfile.TemporaryDirectory() as folder:
            old, current = Path(folder)/'old', Path(folder)/'new'
            runtime.check_ledger_migration(old, current)
            old.write_bytes(b'existing ledger')
            with self.assertRaises(RuntimeError):
                runtime.check_ledger_migration(old, current)
            current.touch()
            with self.assertRaises(RuntimeError):
                runtime.check_ledger_migration(old, current)
            current.write_bytes(old.read_bytes())
            runtime.check_ledger_migration(old, current)
