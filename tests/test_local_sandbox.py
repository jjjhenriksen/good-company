import json
import io
from unittest.mock import patch
from pathlib import Path
import stat
import subprocess
import shutil
import tempfile
import unittest

from good_company.local_sandbox import initialize
from good_company.onboarding import SetupCoordinator


class LocalSandboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plugin = self.root / 'plugin'
        self.plugin.mkdir()
        (self.plugin / 'openclaw.plugin.json').write_text('{}')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name in ('calendar-cli', 'node', 'openclaw.mjs'):
            (self.bin / name).write_text('fixture')

    def tearDown(self):
        self.tmp.cleanup()

    def init(self, **options):
        return initialize(self.root / 'state', Path(__file__).resolve().parents[1], self.plugin,
                          self.bin / 'openclaw.mjs', self.bin / 'node', self.bin, **options)

    def test_separate_paused_ledger_and_no_live_scope_or_send_tools(self):
        result = self.init()
        state = Path(result['state'])
        c = SetupCoordinator(state / 'state.sqlite')
        try:
            self.assertFalse(c.autonomy()['enabled'])
            self.assertEqual(c.events(), [])
            self.assertEqual(c.task_queue(), [])
            self.assertFalse(c.readiness()['ready'])
        finally:
            c.db.close()
        config = json.loads((state / 'openclaw.json').read_text())
        pim = json.loads((state / 'workspace/apple-pim/config.json').read_text())
        self.assertEqual(pim['calendars']['items'], [])
        self.assertFalse(pim['mail']['enabled'])
        self.assertEqual(config['tools']['allow'], ['apple_pim_calendar'])
        self.assertFalse(config['tools']['toolSearch'])
        self.assertTrue(json.loads((state / 'guard-plugin/openclaw.plugin.json').read_text())['activation']['onStartup'])
        self.assertFalse(config['cron']['enabled'])
        self.assertEqual(config['channels'], {})
        self.assertIn('OPENCLAW_SKIP_CHANNELS=1', (state / 'start.sh').read_text())
        self.assertEqual(config['gateway']['bind'], 'loopback')
        self.assertEqual(config['gateway']['auth']['mode'], 'token')
        self.assertNotIn(config['gateway']['auth']['token'], json.dumps(result))
        for name in ('openclaw.json', 'baseline.json', 'state.sqlite'):
            self.assertEqual(stat.S_IMODE((state / name).stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)

    def test_existing_state_refused_without_changes(self):
        self.init()
        state = self.root / 'state'
        before = {p.relative_to(state): p.read_bytes() for p in state.rglob('*') if p.is_file()}
        with self.assertRaises(FileExistsError):
            self.init()
        self.assertEqual(before, {p.relative_to(state): p.read_bytes() for p in state.rglob('*') if p.is_file()})

    def test_missing_installed_plugin_refused_before_state_creation(self):
        (self.plugin / 'openclaw.plugin.json').unlink()
        with self.assertRaises(ValueError):
            self.init()
        self.assertFalse((self.root / 'state').exists())

    def test_tokens_are_fresh_per_install(self):
        self.init()
        first = json.loads((self.root / 'state/openclaw.json').read_text())['gateway']['auth']['token']
        other = initialize(self.root / 'other', Path(__file__).resolve().parents[1], self.plugin,
                           self.bin / 'openclaw.mjs', self.bin / 'node', self.bin)
        second = json.loads((Path(other['state']) / 'openclaw.json').read_text())['gateway']['auth']['token']
        self.assertNotEqual(first, second)

    def test_invalid_model_refused_before_creating_state(self):
        with self.assertRaises(ValueError):
            self.init(model='cloud/provider')
        self.assertFalse((self.root / 'state').exists())

    def test_installed_model_without_tools_refused_before_creating_state(self):
        with patch('good_company.local_sandbox.urllib.request.urlopen', return_value=io.BytesIO(b'{"capabilities":["completion"]}')):
            with self.assertRaisesRegex(ValueError, 'support tools'):
                self.init(model='ollama/fixture')
        self.assertFalse((self.root / 'state').exists())

    def test_tool_model_is_explicit_and_checked_at_loopback(self):
        with patch('good_company.local_sandbox.urllib.request.urlopen', return_value=io.BytesIO(b'{"capabilities":["completion","tools"]}')) as call:
            result = self.init(model='ollama/fixture')
        self.assertEqual(call.call_args.args[0].full_url, 'http://127.0.0.1:11434/api/show')
        config = json.loads((Path(result['state']) / 'openclaw.json').read_text())
        self.assertEqual(config['agents']['defaults']['model']['primary'], 'ollama/fixture')
        self.assertEqual(config['models']['providers']['ollama']['baseUrl'], 'http://127.0.0.1:11434')

    def test_loaded_guard_rejects_mutations_and_per_call_scope_escape(self):
        if not shutil.which('node'):
            self.skipTest('Node is required for the native plugin guard')
        result = self.init()
        state = Path(result['state'])
        code = """
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
const plugin = (await import(pathToFileURL(process.argv[1]).href)).default;
let hook;
plugin.register({ on(name, callback) { assert.equal(name, 'before_tool_call'); hook = callback; } });
for (const action of ['create', 'update', 'delete', 'batch_create', 'events', 'get', 'search']) {
  assert.equal(hook({toolName:'apple_pim_calendar', params:{action}}).block, true);
}
for (const params of [{action:'list',configDir:'/outside'}, {action:'list',profile:'outside'}]) {
  assert.equal(hook({toolName:'apple_pim_calendar',params}).block, true);
}
const allowed = hook({toolName:'apple_pim_calendar',params:{action:'list'}});
assert.equal(allowed.params.configDir, process.argv[2]);
assert.equal(allowed.block, undefined);
"""
        subprocess.run(['node', '--input-type=module', '-e', code, str(state / 'guard-plugin/index.js'),
                        str(state / 'workspace/apple-pim')], check=True, capture_output=True, text=True)
