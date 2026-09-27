import json
from pathlib import Path
import unittest
import test_autonomy as base
from test_core import NOW
from test_task_policy import BeforeLock
from good_company.core import Coordinator


class SourceWithdrawalTests(unittest.TestCase):
    setUp = base.AutonomyTests.setUp
    tearDown = base.AutonomyTests.tearDown

    def test_withdrawn_public_and_private_text_is_unavailable(self):
        for source, audience in [('public', 'volunteer'), ('private', 'coordinator')]:
            self.c.ingest('Packing helpers bring gloves.', source, 'Packing', NOW, audience)
            self.c.withdraw_source(source, 'verified retirement', now=NOW)
        self.assertEqual(self.c.retrieve('packing gloves', 'coordinator', now=NOW)['evidence'], [])
        with self.assertRaises(ValueError):
            self.c.ingest('New gloves.', 'public', 'Packing', NOW)

    def test_withdrawn_event_source_invalidates_and_blocks_reauthorization(self):
        rid = self.c.plan(now=NOW)['automatically_authorized'][0]
        source = self.data['events'][0]['source']
        result = self.c.withdraw_source(source, 'verified retirement', now=NOW)
        self.assertIn(rid, result['pending_reassessment'])
        self.assertEqual(self.c.reminder(rid)['status'], 'superseded')
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_withdrawn_rules_cannot_be_used(self):
        self.c.withdraw_source('demo://fictional-club-dress-code', 'verified retirement', now=NOW)
        self.assertEqual(self.c.plan(now=NOW)['automatically_authorized'], [])

    def test_delete_before_import_lock_prevents_content_reappearing(self):
        source = 'deleted-during-import'
        self.c.ingest('Packing helpers bring gloves.', source, 'Packing', NOW)
        path = self.c.db.execute('PRAGMA database_list').fetchone()[2]
        other = Coordinator(path)
        try:
            self.c.db = BeforeLock(self.c.db, lambda: other.delete_source(source, 'owner deletion', now=NOW))
            with self.assertRaisesRegex(ValueError, 'retired'):
                self.c.ingest('Packing helpers bring new gloves.', source, 'Packing', NOW)
            self.assertEqual(other.db.execute('SELECT count(*) FROM knowledge WHERE source=?', (source,)).fetchone()[0], 0)
            self.assertEqual(other.db.execute('SELECT count(*) FROM document_versions WHERE source=?', (source,)).fetchone()[0], 0)
        finally:
            other.db.close()

    def test_deleted_source_cannot_receive_new_dress_rules(self):
        request = json.loads(Path('examples/dress-code.json').read_text())
        source = request['source']
        self.c.delete_source(source, 'owner deletion', now=NOW)
        with self.assertRaisesRegex(ValueError, 'retired'):
            self.c.set_dress_code(**request, now=NOW)
        self.assertEqual(self.c.db.execute('SELECT count(*) FROM dress_rules WHERE source=?', (source,)).fetchone()[0], 0)
        self.c.set_dress_code(source, [], 'remove residual rules', now=NOW)

    def test_retirement_before_rule_lock_prevents_content_reappearing(self):
        request = json.loads(Path('examples/dress-code.json').read_text())
        source = request['source']
        path = self.c.db.execute('PRAGMA database_list').fetchone()[2]
        other = Coordinator(path)
        try:
            self.c.db = BeforeLock(self.c.db, lambda: other.delete_source(source, 'owner deletion', now=NOW))
            with self.assertRaisesRegex(ValueError, 'retired'):
                self.c.set_dress_code(**request, now=NOW)
            self.assertEqual(other.db.execute('SELECT count(*) FROM dress_rules WHERE source=?', (source,)).fetchone()[0], 0)
        finally:
            other.db.close()
