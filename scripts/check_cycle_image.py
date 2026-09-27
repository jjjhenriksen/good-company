#!/usr/bin/env python3
"""Exercise the image's installed scheduler command without network or services."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

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
    subprocess.run(['good-company-availability', '--help'], cwd=root, env=env,
                   capture_output=True, text=True, check=True)
    (root / 'availability.json').write_text(json.dumps({'journal': 'availability.sqlite',
        'account': 'owner@example.invalid', 'scopes': {'selected': 'calendar@example.invalid'}}))
    result = subprocess.run(['good-company-availability', '--config', str(root / 'availability.json'),
        '--check-id', 'packaging-check', '--scope', 'outside',
        '--start', '2026-09-28T17:00:00Z', '--end', '2026-09-28T18:00:00Z'],
        cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {'status': 'unavailable', 'reason': 'google_calendar_outside_scope'}
    assert not (root / 'availability.sqlite').exists(), 'Out-of-scope check opened provider journal'
print('Installed scheduler command returns paused without credentials or PYTHONPATH.')
print('Installed availability command rejects unknown scope without a provider call.')
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image')
    args = parser.parse_args()
    expected_license = Path(__file__).resolve().parents[1].joinpath('LICENSE').read_text()
    packaged_license = subprocess.run(['docker', 'run', '--rm', '--network', 'none',
        '--entrypoint', 'cat', args.image, '/opt/good-company/LICENSE'],
        text=True, capture_output=True, check=True).stdout
    if packaged_license != expected_license:
        raise SystemExit('The image must retain the exact project license notice.')
    notice_root = Path(__file__).resolve().parents[1] / 'third_party'
    expected_notices = {p.relative_to(notice_root).as_posix():
        hashlib.sha256(p.read_bytes()).hexdigest()
        for p in notice_root.rglob('*') if p.is_file()}
    notice_check = """import hashlib, json; from pathlib import Path
root = Path('/opt/good-company/third_party')
print(json.dumps({p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in root.rglob('*') if p.is_file()}))"""
    actual_notices = subprocess.run(['docker', 'run', '--rm', '--network', 'none',
        '--entrypoint', 'python3', args.image, '-c', notice_check],
        text=True, capture_output=True, check=True).stdout
    if json.loads(actual_notices) != expected_notices:
        raise SystemExit('The image must retain every exact third-party notice.')
    subprocess.run(['docker', 'run', '--rm', '--network', 'none', '-i',
                    '--entrypoint', 'python3', args.image, '-'], input=SCRIPT,
                   text=True, check=True)


if __name__ == '__main__':
    main()
