import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_cli(self, database, request):
        return subprocess.run([sys.executable, '-m', 'good_company.cli', '--db', str(database), 'queue'],
                              input=request, text=True, capture_output=True)

    def test_non_object_is_a_structured_error_without_database_creation(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'state.sqlite'
            result=self.run_cli(db,'[]')
            self.assertEqual(result.returncode,2)
            self.assertIn('JSON object',json.loads(result.stderr)['error'])
            self.assertFalse(db.exists())

    def test_corrupt_database_is_a_structured_error(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'state.sqlite';db.write_bytes(b'not a sqlite database')
            result=self.run_cli(db,'{}')
            self.assertEqual(result.returncode,2)
            self.assertIn('database',json.loads(result.stderr)['error'])
            self.assertEqual(result.stdout,'')

    def test_simulated_time_is_rejected_before_database_creation(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'state.sqlite'
            result=self.run_cli(db,'{"now":"2026-09-25T00:00:00Z"}')
            self.assertEqual(result.returncode,2)
            self.assertIn('real clock',json.loads(result.stderr)['error'])
            self.assertFalse(db.exists())
