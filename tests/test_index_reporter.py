"""Exercise the packaged upstream usage collector with isolated fictional stores."""
import contextlib
import types
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLIENT = Path('/opt/plow/agent-index-client.py')
if not CLIENT.exists():
    CLIENT = ROOT / 'third_party/agent-index-client/agent_index_client.py'

# A Zstandard raw-block frame: valid without needing a compressor dependency.
def compressed_event(event):
    raw = json.dumps(event).encode()
    assert 256 <= len(raw) < 65536
    header = b'\x28\xb5\x2f\xfd\x60' + (len(raw) - 256).to_bytes(2, 'little')
    return header + ((len(raw) << 3) | 1).to_bytes(3, 'little') + raw


class IndexReporterTests(unittest.TestCase):
    def setUp(self):
        # Compile without writing __pycache__ beside the vendored source: those
        # generated files must not enter the exact third-party package manifest.
        self.client = types.ModuleType('fixture_index_client')
        self.client.__file__ = str(CLIENT)
        exec(compile(CLIENT.read_bytes(), str(CLIENT), 'exec'), self.client.__dict__)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def event(self, response, tokens, big=False):
        event = {'type': 'message', 'timestamp': '2026-09-27T10:00:00Z',
                 'message': {'role': 'assistant', 'model': 'fictional-model',
                             'responseId': response, 'usage': {'input': tokens, 'output': 2}}}
        if big:
            event['filler'] = 'fictional ' * 200
        return event

    def store(self, compressed=True, corrupt=False):
        path = self.root / 'agents/main/agent/openclaw-agent.sqlite'
        path.parent.mkdir(parents=True)
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE transcript_events (event_json TEXT, created_at INTEGER' +
                   (', event_zstd BLOB, event_utf8_bytes INTEGER' if compressed else '') + ')')
        small, large = self.event('small', 11), self.event('large', 100, True)
        now = int(time.time() * 1000)
        if compressed:
            db.execute('INSERT INTO transcript_events VALUES (?, ?, NULL, NULL)', (json.dumps(small), now))
            blob = b'corrupt frame' if corrupt else compressed_event(large)
            db.execute('INSERT INTO transcript_events VALUES (NULL, ?, ?, ?)',
                       (now, blob, len(json.dumps(large).encode())))
        else:
            for event in (small, large):
                db.execute('INSERT INTO transcript_events VALUES (?, ?)', (json.dumps(event), now))
        db.commit()
        db.close()
        return path

    def collect(self):
        return self.client.from_openclaw(28, state=str(self.root))

    def test_mixed_compressed_and_plain_usage_is_complete(self):
        self.store()
        result = self.collect()
        self.assertEqual(result['2026-09-27']['fictional-model'],
                         {'input': 111, 'output': 4, 'cache_read': 0, 'cache_write': 0})
        self.assertEqual(self.client.FAILURES, [])

    def test_legacy_store_without_compression_columns(self):
        self.store(compressed=False)
        self.assertEqual(self.collect()['2026-09-27']['fictional-model']['input'], 111)
        self.assertEqual(self.client.FAILURES, [])

    def test_corrupt_compressed_event_blocks_partial_post(self):
        self.store(corrupt=True)
        with patch.dict(os.environ, {'OPENCLAW_STATE_DIR': str(self.root)}), \
             patch.object(self.client, 'auth_headers', return_value={}), \
             patch.object(self.client, 'from_agentsview', return_value={}), \
             patch.object(self.client, 'from_hermes', return_value={}), \
             patch.object(self.client, '_post', return_value=(200, 'fictional')) as post, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, 'NOT reporting a partial total'):
                self.client.main(['--agent', 'fictional-agent'])
        post.assert_not_called()
        self.assertTrue(self.client.FAILURES)

    def test_missing_decoder_is_failure(self):
        self.store()
        with patch.object(self.client, '_zstd_decoder', return_value=None):
            self.collect()
        self.assertIn('no zstd decoder', self.client.FAILURES[0])

    def test_compressed_response_deduplicates(self):
        path = self.store()
        with sqlite3.connect(path) as db:
            db.execute('INSERT INTO transcript_events SELECT * FROM transcript_events WHERE event_zstd IS NOT NULL')
        self.assertEqual(self.collect()['2026-09-27']['fictional-model']['input'], 111)
