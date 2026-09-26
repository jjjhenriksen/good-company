import json
import tempfile
import unittest
from pathlib import Path
from good_company.onboarding import SetupCoordinator


class OnboardingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'state.sqlite'
        self.c = SetupCoordinator(self.path)
        self.profile = json.loads(Path('examples/profile.json').read_text())['profile']
        self.policy = json.loads(Path('examples/autonomy.json').read_text())['policy']

    def tearDown(self):
        self.c.db.close()
        self.tmp.cleanup()

    def test_preview_does_not_grant_authority(self):
        result = self.c.onboarding(self.profile, self.policy, 'owner conversation')
        self.assertEqual(result['status'], 'preview')
        self.assertIsNone(self.c.autonomy())

    def test_apply_survives_restart_and_repeats_without_change(self):
        result = self.c.onboarding(self.profile, self.policy, 'owner conversation', True)
        self.assertTrue(result['changed'])
        self.c.db.close()
        self.c = SetupCoordinator(self.path)
        self.assertEqual(self.c.profile(), self.profile)
        self.assertEqual(self.c.autonomy(), self.policy)
        self.assertFalse(self.c.onboarding(self.profile, self.policy, 'owner conversation', True)['changed'])

    def test_invalid_remit_preserves_existing_settings(self):
        self.c.onboarding(self.profile, self.policy, 'owner conversation', True)
        self.profile['organization'] = 'Another group'
        self.policy['sender'] = 'invalid'
        with self.assertRaises(ValueError):
            self.c.onboarding(self.profile, self.policy, 'owner conversation', True)
        self.assertNotEqual(self.c.profile()['organization'], 'Another group')

    def test_empty_install_asks_for_scope(self):
        self.assertEqual(self.c.onboarding()['status'], 'needs_context')
        self.assertIsNone(self.c.autonomy())
