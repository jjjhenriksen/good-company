import json
import unittest
from datetime import timedelta
from test_readiness import ReadinessTests
from test_core import NOW
from good_company.core import stamp


class HealthTests(ReadinessTests):
    def test_unchanged_failure_is_quiet_and_recovery_is_reported(self):
        self.assertTrue(self.c.health(now=NOW)['notify'])
        self.assertFalse(self.c.health(now=NOW)['notify'])
        self.configured()
        self.assertTrue(self.c.health(now=NOW)['notify'])
        self.assertFalse(self.c.health(now=NOW)['notify'])
        self.assertTrue(self.c.health(now=stamp(NOW)+timedelta(hours=1))['notify'])

    def test_missing_credentials_are_explicit_without_evidence_leak(self):
        self.configured()
        self.c.record_connection('mail', 'missing_credentials', 'SECRET-REF', NOW, now=NOW)
        report = self.c.health(now=NOW)
        self.assertEqual(report['health']['connections']['mail'], 'missing_credentials')
        self.assertNotIn('SECRET-REF', json.dumps(report))
        self.assertNotIn('@', json.dumps(report))
