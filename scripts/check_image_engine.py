#!/usr/bin/env python3
"""Run regressions against installed image code, without mounting the source engine."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


CHECK = r'''
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
import good_company

root = Path(good_company.__file__).resolve().parent
assert root == Path('/opt/good-company/good_company'), 'Tests must use the installed engine'
expected = json.loads(Path('/checks/expected_modules.json').read_text())
actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in root.rglob('*.py')}
assert actual == expected, 'Installed modules differ from the selected source checkout'
reporter = Path('/opt/plow/agent-index-client.py')
assert hashlib.sha256(reporter.read_bytes()).hexdigest() == Path('/checks/expected_reporter_sha256.txt').read_text(), 'Installed reporter differs from the pinned source'
print(f'Verified {len(actual)} installed modules and the pinned reporter; no source engine mounted.', flush=True)
suite = unittest.defaultTestLoader.discover('/checks/tests')
result = unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():
    sys.exit(1)
for demo in ('demo.py', 'autonomous_demo.py'):
    subprocess.run([sys.executable, '/checks/scripts/' + demo], check=True,
                   stdout=subprocess.DEVNULL)
print('Both fictional demos passed against the installed engine.', flush=True)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tracked = subprocess.check_output(['git', 'ls-files', '-z', 'tests', 'scripts', 'good_company'],
                                     cwd=root).decode().split('\0')
    with tempfile.TemporaryDirectory(prefix='good-company-image-tests-') as directory:
        staging = Path(directory)
        expected = {}
        for name in filter(None, tracked):
            source = root / name
            relative = Path(name)
            if relative.parts[0] == 'good_company':
                if source.suffix == '.py':
                    expected[relative.relative_to('good_company').as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
            else:
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        if not expected or not (staging / 'tests').is_dir():
            raise SystemExit('Run from a checkout with tracked engine and test files.')
        # Fixtures come from the image too; no local credentials or source tree.
        (staging / 'examples').symlink_to('/opt/good-company/examples')
        (staging / 'expected_modules.json').write_text(json.dumps(expected))
        (staging / 'expected_reporter_sha256.txt').write_text(hashlib.sha256(
            (root / 'third_party/agent-index-client/agent_index_client.py').read_bytes()).hexdigest())
        # The image's unprivileged node user must be able to read the host mount.
        staging.chmod(0o755)
        subprocess.run(['docker', 'run', '--rm', '--network', 'none', '--read-only',
                        '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m',
                        '--mount', f'type=bind,src={staging},dst=/checks,readonly',
                        '--workdir', '/checks', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                        '--entrypoint', 'python3', args.image, '-c', CHECK], check=True)


if __name__ == '__main__':
    main()
