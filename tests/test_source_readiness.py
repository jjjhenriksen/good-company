import json
import unittest

import test_readiness as fixtures
from test_core import NOW


class SourceReadinessTests(unittest.TestCase):
    setUp = fixtures.ReadinessTests.setUp
    tearDown = fixtures.ReadinessTests.tearDown
    configured = fixtures.ReadinessTests.configured

    def source(self, version='v1', **changes):
        metadata = dict(version=version, original_source='private://source',
                        review_authority='private reviewer', effective_from='2026-09-01',
                        effective_until='2026-10-01', review_by='2026-10-01')
        metadata.update(changes)
        self.c.ingest('Packing requires private fixture gloves.', 'private-source',
                      'Private title', NOW, metadata=metadata)

    def test_recent_import_does_not_make_expired_review_ready(self):
        self.configured()
        self.source(review_by='2026-09-24')
        self.assertEqual(self.c.retrieve('packing', now=NOW)['evidence'], [])
        state = self.c.readiness(now=NOW)
        self.assertFalse(state['ready'])
        self.assertEqual(state['sources']['status'], 'needs_review')

    def test_future_only_or_expired_effective_version_needs_review(self):
        self.configured()
        self.source(effective_from='2026-10-01', effective_until='2026-11-01')
        self.assertFalse(self.c.readiness(now=NOW)['ready'])
        self.assertEqual(self.c.readiness(now=NOW)['sources']['review_gaps'], 1)
        self.source('expired', effective_from='2026-08-01', effective_until='2026-09-01')
        self.assertFalse(self.c.readiness(now=NOW)['ready'])

    def test_overlapping_current_versions_need_review(self):
        self.configured()
        self.source()
        self.source('v2', effective_from='2026-09-15')
        state = self.c.readiness(now=NOW)
        self.assertFalse(state['ready'])
        self.assertEqual(state['sources']['review_gaps'], 1)
        self.assertEqual(state['sources']['documents'], 1)

    def test_valid_current_version_with_past_and_future_versions_is_ready(self):
        self.configured()
        self.source('old', effective_from='2026-08-01', effective_until='2026-09-01',
                    review_by='2026-08-31')
        self.source('current')
        self.source('future', effective_from='2026-10-01', effective_until='2026-11-01',
                    review_by='2026-11-01')
        state = self.c.readiness(now=NOW)
        self.assertTrue(state['ready'], state)
        self.assertEqual(state['sources']['status'], 'current')
        self.assertEqual(state['sources']['review_gaps'], 0)

    def test_recent_legacy_content_needs_review_and_withdrawal_excludes_it(self):
        self.configured()
        self.c.ingest('Packing legacy text.', 'legacy', 'Legacy', NOW)
        state = self.c.readiness(now=NOW)
        self.assertFalse(state['ready'])
        self.assertEqual(state['sources']['unreviewed'], 1)
        self.assertEqual(state['sources']['stale'], 0)
        self.c.withdraw_source('legacy', 'fixture withdrawal', now=NOW)
        state = self.c.readiness(now=NOW)
        self.assertEqual(state['sources']['documents'], 0)
        self.assertEqual(state['sources']['status'], 'not_supplied')
        self.assertTrue(state['ready'])

    def test_stale_legacy_dates_are_counted_without_dismissing_valid_reviews(self):
        self.configured()
        self.c.ingest('Packing historical content.', 'legacy', 'Legacy', '2026-01-01T00:00:00Z')
        self.assertEqual(self.c.readiness(now=NOW)['sources']['stale'], 1)
        metadata = dict(version='reviewed', original_source='private://source',
                        review_authority='private reviewer', effective_from='2026-01-01',
                        review_by='2027-01-01')
        self.c.ingest('Packing historical content.', 'legacy', 'Legacy', '2026-01-01T00:00:00Z',
                      metadata=metadata)
        state = self.c.readiness(now=NOW)
        self.assertTrue(state['ready'], state)
        self.assertEqual(state['sources']['stale'], 0)

    def test_health_reports_review_gap_and_recovery_without_private_details(self):
        self.configured()
        self.c.ingest('Private legacy gloves.', 'private-source', 'Private title', NOW, 'coordinator')
        report = self.c.health(now=NOW)
        self.assertTrue(report['notify'])
        self.assertFalse(report['health']['ready'])
        self.assertFalse(self.c.health(now=NOW)['notify'])
        metadata = dict(version='reviewed', original_source='private://source',
                        review_authority='private reviewer', effective_from='2026-09-01',
                        review_by='2026-10-01')
        self.c.ingest('Private legacy gloves.', 'private-source', 'Private title', NOW, 'coordinator', metadata)
        recovery = self.c.health(now=NOW)
        self.assertTrue(recovery['notify'])
        self.assertTrue(recovery['health']['ready'])
        self.assertFalse(self.c.health(now=NOW)['notify'])
        for private in ('private-source', 'Private title', 'gloves', 'private reviewer', 'private://'):
            self.assertNotIn(private, json.dumps([report, recovery]))
