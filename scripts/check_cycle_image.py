#!/usr/bin/env python3
"""Exercise the image's installed scheduler command without network or services."""
import argparse
import subprocess

SCRIPT = r'''
import json
import os
from pathlib import Path
import subprocess
import tempfile

env = dict(os.environ)
env.pop('PYTHONPATH', None)
env.pop('PLOW_API_BASE', None)
env.pop('PLOW_AGENT_TOKEN', None)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'cycle.json').write_text(json.dumps({'db': 'state.sqlite', 'journal': 'latch.sqlite'}))
    result = subprocess.run(['good-company-cycle', '--config', str(root / 'cycle.json'),
        '--cycle-id', 'packaging-check', '--start', '2026-09-26T00:00:00Z',
        '--end', '2026-09-27T00:00:00Z'], cwd=root, env=env,
        capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'status': 'paused', 'cycle_id': 'packaging-check'}
    assert not (root / 'latch.sqlite').exists(), 'Paused entrypoint opened provider journal'
print('Installed scheduler command returns paused without credentials or PYTHONPATH.')
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    args = parser.parse_args()
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '-i',
                    '--entrypoint', 'python3', args.image, '-'], input=SCRIPT,
                   text=True, check=True)


if __name__ == '__main__':
    main()
