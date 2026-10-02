#!/usr/bin/env python3
"""Exercise fictional nonprofit workflows over a private loopback mailbox."""
import argparse
import importlib
import io
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
SCENARIOS = {58: ('test_food_bank_lab', 'FoodBankLabTests')}


def run(issues=None):
    report = {'evidence_kind': 'isolated_loopback_lab', 'live_provider_acceptance': False,
              'external_mail_sent': False, 'scenarios': {}}
    for issue in issues or sorted(SCENARIOS):
        module_name, class_name = SCENARIOS[issue]
        module = importlib.import_module(module_name)
        module.OBSERVED.clear()
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(getattr(module, class_name))
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        report['scenarios'][str(issue)] = {'passed': result.wasSuccessful(), 'checks': result.testsRun,
            'failed_checks': [test.id() for test, _ in result.failures + result.errors],
            'observed': dict(module.OBSERVED) if result.wasSuccessful() else {},
            'issue_accepted': False,
            'remaining': 'Authorized real mailbox, native identity proof and genuine delivery acceptance.'}
    report['passed'] = all(s['passed'] for s in report['scenarios'].values())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', type=int, choices=sorted(SCENARIOS), action='append')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = run(args.issue)
    output = json.dumps(report, indent=2) + '\n'
    if args.report:
        with os.fdopen(os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            stream.write(output)
    print(output)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
