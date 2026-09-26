from datetime import timedelta
import json
import test_onboarding as setup
import unittest
from test_core import NOW, snapshot
from good_company.core import stamp


class ReadinessTests(unittest.TestCase):
    setUp = setup.OnboardingTests.setUp
    tearDown = setup.OnboardingTests.tearDown
    def configured(self):
        self.c.onboarding(self.profile, self.policy, 'owner reference', True)
        self.c.import_calendar(snapshot(), now=NOW)
        for component in ('calendar', 'mail', 'scheduler'):
            self.c.record_connection(component, 'verified', 'private://sensitive-evidence', NOW, now=NOW)

    def test_empty_state_is_not_ready(self):
        self.assertFalse(self.c.readiness(now=NOW)['ready'])

    def test_healthy_state_and_evidence_redaction(self):
        self.configured()
        result = self.c.readiness(now=NOW)
        self.assertTrue(result['ready'], result)
        self.assertNotIn('sensitive-evidence', json.dumps(result))
        self.assertNotIn('example.invalid', json.dumps(result))

    def test_stale_or_changed_remit_is_not_ready(self):
        self.configured()
        self.assertFalse(self.c.readiness(now=stamp(NOW) + timedelta(hours=1))['ready'])
        self.policy['max_reminders_per_day'] = 2
        self.c.configure_autonomy(self.policy, 'changed remit', now=NOW)
        self.assertFalse(self.c.readiness(now=NOW)['ready'])

    def test_future_observation_rejected(self):
        with self.assertRaises(ValueError):
            self.c.record_connection('mail', 'verified', 'evidence', stamp(NOW) + timedelta(seconds=1), now=NOW)
