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

    def test_implicit_applicability_uses_local_date_in_both_offset_directions(self):
        cases = [
            ('America/Los_Angeles', '2026-10-01T00:30:00Z', '2026-09-30', '2026-10-01'),
            ('Asia/Tokyo', '2026-09-30T16:30:00Z', '2026-10-01', '2026-10-02'),
        ]
        self.configured()
        for zone, now, start, end in cases:
            with self.subTest(zone=zone):
                profile = self.c.profile()
                profile['timezone'] = zone
                self.c.configure(profile)
                source = 'source-' + zone
                metadata = dict(version='v1', original_source='fixture://local-date',
                                review_authority='fixture reviewer', effective_from=start,
                                effective_until=end, review_by='2027-01-01')
                self.c.ingest('Packing calendar policy.', source, 'Fixture', NOW, metadata=metadata)
                evidence = self.c.retrieve('packing', now=now)['evidence']
                self.assertIn(source, {item['source'] for item in evidence})
                self.c.withdraw_source(source, 'fixture cleanup', now=now)

    def test_local_expiry_and_review_deadline_match_retrieval_and_readiness(self):
        self.configured()
        profile = self.c.profile()
        profile['timezone'] = 'Asia/Tokyo'
        self.c.configure(profile)
        now = '2026-09-30T16:30:00Z'  # October 1 locally.
        for field in ('effective_until', 'review_by'):
            with self.subTest(field=field):
                changes = {field: '2026-10-01' if field == 'effective_until' else '2026-09-30'}
                metadata = dict(version=field, original_source='fixture://deadline',
                                review_authority='fixture reviewer', effective_from='2026-09-01',
                                effective_until='2026-11-01', review_by='2026-10-01')
                metadata.update(changes)
                self.c.ingest('Packing calendar policy.', 'deadline-' + field, 'Fixture',
                              NOW, metadata=metadata)
                self.assertEqual(self.c.retrieve('packing', now=now)['evidence'], [])
                self.assertEqual(self.c.readiness(now=now)['sources']['status'], 'needs_review')

    def test_local_review_day_and_explicit_requested_date_are_preserved(self):
        self.configured()
        now = '2026-10-01T00:30:00Z'  # September 30 in the configured Los Angeles zone.
        self.source(review_by='2026-09-30')
        self.assertTrue(self.c.retrieve('packing', now=now)['evidence'])
        self.assertEqual(self.c.readiness(now=now)['sources']['status'], 'current')
        self.assertEqual(self.c.retrieve('packing', on='2026-10-01', now=now)['evidence'], [])
