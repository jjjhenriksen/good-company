import unittest
import test_core as base
from test_core import NOW


class SourceVersionTests(unittest.TestCase):
    setUp = base.CoordinationTests.setUp
    tearDown = base.CoordinationTests.tearDown

    def meta(self, version, start, end=None):
        return dict(version=version, original_source='fixture://handbook', review_authority='verified fictional review',
                    effective_from=start, effective_until=end, review_by='2027-01-01')

    def test_historical_applicability_and_immutable_versions(self):
        self.c.ingest('Packing requires blue gloves.', 'handbook', 'Packing', NOW, metadata=self.meta('v1', '2026-01-01', '2026-09-01'))
        self.c.ingest('Packing requires green gloves.', 'handbook', 'Packing', NOW, metadata=self.meta('v2', '2026-09-01'))
        old = self.c.retrieve('packing gloves', on='2026-08-01', now=NOW)
        self.assertIn('blue', old['evidence'][0]['content'])
        self.assertNotIn('blue', str(self.c.retrieve('packing gloves', now=NOW)))
        with self.assertRaises(ValueError):
            self.c.ingest('Changed text.', 'handbook', 'Packing', NOW, metadata=self.meta('v2', '2026-09-01'))

    def test_expired_review_has_gap_and_no_evidence(self):
        meta = self.meta('v1', '2026-01-01')
        meta['review_by'] = '2026-01-02'
        self.c.ingest('Packing requires gloves.', 'handbook', 'Packing', NOW, metadata=meta)
        result = self.c.retrieve('packing gloves', now=NOW)
        self.assertEqual(result['evidence'], [])
        self.assertEqual(result['gaps'][0]['reason'], 'review_overdue')

    def test_private_reclassification_gates_prior_versions(self):
        self.c.ingest('Packing blue gloves.', 'handbook', 'Packing', NOW, metadata=self.meta('v1', '2026-01-01', '2026-09-01'))
        self.c.ingest('Packing private gloves.', 'handbook', 'Packing', NOW, 'coordinator', self.meta('v2', '2026-09-01'))
        self.assertEqual(self.c.retrieve('packing gloves', on='2026-08-01', now=NOW)['evidence'], [])
