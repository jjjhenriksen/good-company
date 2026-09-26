import unittest
import test_autonomy as base
from test_core import NOW


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
