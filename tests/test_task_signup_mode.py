import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_tasks as base
from test_core import NOW


class TaskSignupModeTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_non_boolean_signup_modes_leave_task_and_audit_unchanged(self):
        before = list(self.c.db.iterdump())
        for index, value in enumerate(('false', 'true', 0, 1, None, [], {})):
            with self.subTest(value=value):
                task = dict(base.task('candidate-' + str(index)), signup_required=value)
                with self.assertRaisesRegex(ValueError, 'signup_required must be boolean'):
                    self.c.add_task(task, 'fixture source', now=NOW)
                self.assertEqual(list(self.c.db.iterdump()), before)

    def test_explicit_signup_mode_requires_offer_while_false_and_default_delegate(self):
        self.c.close_task('chairs', 'cancelled', 'fixture setup', now=NOW)
        for name, value in (('optin', True), ('automatic', False), ('legacy', 'omit')):
            task = base.task(name)
            if value != 'omit':
                task['signup_required'] = value
            self.c.add_task(task, 'fixture source', now=NOW)
        result = self.c.delegate(now=NOW)
        self.assertEqual({row['task_id'] for row in result['assigned']}, {'automatic', 'legacy'})
        self.assertFalse(self.c.db.execute("SELECT 1 FROM assignments WHERE task_id='optin'").fetchone())

    def test_cli_rejects_invalid_signup_mode_before_creating_state(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'untouched.sqlite'
            request = {'task': dict(base.task(), signup_required='false'), 'authority': 'fixture source'}
            result = subprocess.run([sys.executable, '-m', 'good_company.cli', '--db', str(db), 'add-task'],
                                    input=json.dumps(request).encode(), capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(db.exists())
            self.assertNotIn(b'Traceback', result.stderr)

    def test_legacy_invalid_mode_defers_without_blocking_other_tasks(self):
        task = dict(base.task('invalid'), signup_required='false')
        with self.c.db:
            self.c.db.execute("INSERT INTO tasks VALUES(?,?,'open')", (task['id'], json.dumps(task)))
        result = self.c.delegate(now=NOW)
        self.assertEqual([row['task_id'] for row in result['assigned']], ['chairs'])
        self.assertTrue(any(row.get('task_id') == 'invalid' and 'signup_required' in row['reason'] for row in result['exceptions']))
        self.assertFalse(self.c.db.execute("SELECT 1 FROM assignments WHERE task_id='invalid'").fetchone())

    def test_legacy_invalid_mode_cannot_claim_existing_assignment(self):
        self.c.delegate(now=NOW)
        notice = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        task = dict(base.task(), signup_required=0)
        with self.c.db:
            self.c.db.execute('UPDATE tasks SET payload=? WHERE id=?', (json.dumps(task), task['id']))
        with self.assertRaisesRegex(ValueError, 'signup_required must be boolean'):
            self.c.task_claim(notice['id'], now=NOW)
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == notice['id'])['status'], 'pending')

    def test_legacy_invalid_signup_cannot_reserve_or_record_reply(self):
        from test_signups import SignupTests
        from good_company.signups import apply
        fixture = SignupTests()
        fixture.setUp()
        try:
            fixture.prepare()
            row = fixture.c.db.execute("SELECT payload FROM tasks WHERE id='packing:one'").fetchone()
            task = dict(json.loads(row[0]), signup_required='true')
            with fixture.c.db:
                fixture.c.db.execute("UPDATE tasks SET payload=? WHERE id='packing:one'", (json.dumps(task),))
            before = list(fixture.c.db.iterdump())
            with self.assertRaisesRegex(ValueError, 'signup_required must be boolean'):
                apply(fixture.c, fixture.reply('alex', 'signup', 'invalid-mode'), 'invalid-mode', now=NOW)
            self.assertEqual(list(fixture.c.db.iterdump()), before)
        finally:
            fixture.tearDown()
