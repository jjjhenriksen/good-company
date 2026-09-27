"""Local preflight only. Does not send messages or establish live acceptance."""
from pathlib import Path
import json, os, subprocess, sys, unittest
ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
MODULES = ['test_mixed_roles', 'test_dress_code', 'test_source_withdrawal', 'test_source_authority', 'test_participant']
suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
result = unittest.TextTestRunner(verbosity=1).run(suite)
report = {'issue': 62, 'scope': 'local preflight using existing fictional contract fixtures',
          'commit': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
          'tests_run': result.testsRun, 'passed': result.wasSuccessful(),
          'live_acceptance': 'pending', 'provider_receipts': [], 'messages_sent': 0}
print(json.dumps(report, indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
