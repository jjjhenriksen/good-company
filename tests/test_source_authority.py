import copy
import json
from pathlib import Path
import unittest
import test_autonomy as base
from test_core import NOW


class SourceAuthorityTests(unittest.TestCase):
    setUp = base.AutonomyTests.setUp
    tearDown = base.AutonomyTests.tearDown

    def conflict(self):
        rule = json.loads(Path('examples/dress-code.json').read_text())['rules'][0]
        rule['attire'] = 'A documented alternative outfit.'
        self.c.set_dress_code('exception', [rule], 'verified exception', now=NOW)
        self.c.ingest('For this service activity the exception source supersedes the handbook.', 'decision', 'Authority', NOW)
        return {'preferred_source': 'exception', 'overridden_source': 'demo://fictional-club-dress-code',
                'evidence_source': 'decision', 'section': 'Supplied decision section 1', 'event_type': 'service activity',
                'role': 'member', 'effective_from': '2026-09-01', 'effective_until': '2026-10-01', 'review_by': '2026-10-01'}

    def resolve(self):
        return self.c.dress_code(event_type='service activity', role='member', on='2026-09-27', now=NOW)

    def test_supplied_precedence_resolves_without_deleting_other_source(self):
        rule = self.conflict()
        self.assertEqual(self.resolve()['status'], 'needs_review')
        self.c.set_source_precedence(rule, 'verified governing decision', now=NOW)
        result = self.resolve()
        self.assertEqual(result['status'], 'supported')
        self.assertIn('alternative', result['attire'])
        self.assertEqual(len(result['citations']), 2)
        self.assertEqual(result['precedence'][0]['evidence_source'], 'decision')

    def test_withdrawn_or_private_authority_does_not_resolve_public_answer(self):
        rule = self.conflict()
        self.c.set_source_precedence(rule, 'verified decision', now=NOW)
        self.c.ingest('Private governing decision.', 'decision', 'Authority', NOW, 'coordinator')
        self.assertEqual(self.resolve()['status'], 'needs_review')
        self.c.withdraw_source('decision', 'withdrawal', now=NOW)
        self.assertEqual(self.resolve()['status'], 'needs_review')

    def test_precedence_cycles_are_rejected(self):
        rule = self.conflict()
        self.c.set_source_precedence(rule, 'verified decision', now=NOW)
        rule['preferred_source'], rule['overridden_source'] = rule['overridden_source'], rule['preferred_source']
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            self.c.set_source_precedence(rule, 'conflicting decision', now=NOW)
