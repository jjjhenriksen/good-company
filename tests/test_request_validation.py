import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from good_company.validation import validate_request, RequestError


class RequestValidationTests(unittest.TestCase):
    def test_nested_wrong_types_are_rejected(self):
        for request in [{'snapshot': {'events': ['not-an-event']}}, {'volunteer': {'availability': [1]}},
                        {'policy': {'allowed_recipients': [['nested']]}}, {'task': {'required_skills': {'packing': True}}}]:
            with self.assertRaises(RequestError):
                validate_request(request)

    def test_user_defined_map_names_are_not_schema_fields(self):
        validate_request({'task': {'required_skills': {'organization': 2, 'roles': 1}},
                          'profile': {'program_audiences': {'title': ['fixture@example.org']}}})

    def test_oversized_input_is_rejected_before_database_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'untouched.sqlite'
            result = subprocess.run([sys.executable, '-m', 'good_company.cli', '--db', str(db), 'configure'],
                                    input=b'x' * 2_000_001, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(db.exists())
            self.assertNotIn(b'Traceback', result.stderr)

    def test_malformed_private_date_does_not_echo_value(self):
        with tempfile.TemporaryDirectory() as folder:
            request = {'text': 'fixture text', 'source': 'fixture', 'title': 'Fixture', 'updated': 'PRIVATE-DATE-MARKER'}
            result = subprocess.run([sys.executable, '-m', 'good_company.cli', '--db', str(Path(folder)/'db.sqlite'), 'ingest'],
                                    input=json.dumps(request).encode(), capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(b'PRIVATE-DATE-MARKER', result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)
