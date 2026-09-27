from datetime import timedelta
import json
import unittest
import test_tasks as base
from test_core import NOW
from good_company.core import stamp


class LifecycleTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_summary_excludes_private_fields(self):
        self.c.delegate(now=NOW)
        result = self.c.export_summary('owner export request')
        self.assertEqual(result['counts']['volunteers'], 2)
        self.assertNotIn('example.invalid', json.dumps(result))
        self.assertNotIn('organizing', json.dumps(result))

    def test_source_content_deletion_keeps_withdrawal_tombstone(self):
        self.c.ingest('Private volunteer packing details.', 'private-source', 'Private', NOW, 'coordinator')
        self.c.delete_source('private-source', 'owner deletion request', now=NOW)
        self.assertEqual(self.c.db.execute('SELECT count(*) FROM document_versions').fetchone()[0], 0)
        self.assertTrue(self.c._source_retired('private-source'))

    def test_source_deletion_removes_all_its_translation_copies_only(self):
        for source, text in [('guide', 'Packing helpers arrive at noon.'),
                             ('guide', 'Packing helpers arrive at one.'),
                             ('other-guide', 'Packing helpers bring gloves.')]:
            self.c.ingest(text, source, 'Guide', NOW)
            row = self.c.db.execute('SELECT section FROM knowledge WHERE source=?', (source,)).fetchone()
            self.c.register_translation(source=source, section=row[0], original=text,
                                        translated='Traducción revisada de prueba.', language='es',
                                        authority='fictional reviewer', now=NOW)
        self.assertEqual(self.c.db.execute("SELECT count(*) FROM settings WHERE key LIKE 'translation:%'").fetchone()[0], 3)
        self.c.delete_source('guide', 'owner deletion request', now=NOW)
        translations = [json.loads(row[0]) for row in self.c.db.execute("SELECT value FROM settings WHERE key LIKE 'translation:%'")]
        self.assertEqual([item['source'] for item in translations], ['other-guide'])
        self.assertEqual(translations[0]['original'], 'Packing helpers bring gloves.')
        self.assertTrue(self.c._source_retired('guide'))
        self.assertFalse(self.c._source_retired('other-guide'))
        self.assertIsNotNone(self.c.autonomy())
        self.c.delete_source('guide', 'repeat owner deletion request', now=NOW)
        self.assertEqual(self.c.db.execute("SELECT count(*) FROM settings WHERE key LIKE 'translation:%'").fetchone()[0], 1)

    def test_retention_does_not_replay_finalized_send(self):
        self.c.delegate(now=NOW)
        nid = next(n['id'] for n in self.c.task_queue() if n['kind'] == 'assignment')
        self.c.task_claim(nid, now=NOW)
        self.c.task_receipt(nid, 'sent', 'fixture-receipt', now=NOW)
        later = stamp(NOW) + timedelta(days=2)
        result = self.c.retain_delivery_history(stamp(NOW) + timedelta(days=1), 'owner retention request', now=later)
        self.assertEqual(result['redacted_messages'], 1)
        with self.assertRaises(ValueError):
            self.c.task_claim(nid, now=NOW)
        self.assertEqual(next(n for n in self.c.task_queue() if n['id'] == nid)['receipt'], 'fixture-receipt')
