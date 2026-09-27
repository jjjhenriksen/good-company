#!/usr/bin/env python3
"""Smoke-test the installed distribution outside the source checkout."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('wheel', type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='good-company-wheel-') as directory:
        target = Path(directory)
        venv.EnvBuilder(with_pip=True).create(target/'env')
        bindir = target/'env'/('Scripts' if os.name == 'nt' else 'bin')
        python = bindir/('python.exe' if os.name == 'nt' else 'python')
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-index', str(wheel)],
                       cwd=target, check=True)
        cli = bindir/('good-company.exe' if os.name == 'nt' else 'good-company')
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        env.pop('GOOD_COMPANY_DB', None)
        cycle = bindir/('good-company-cycle.exe' if os.name == 'nt' else 'good-company-cycle')
        subprocess.run([str(cycle), '--help'], cwd=target, env=env, check=True, capture_output=True)
        result = subprocess.run([str(cli), 'configure', '--input', str(root/'examples/profile.json')],
                                cwd=target, env=env, check=True, capture_output=True, text=True)
        assert json.loads(result.stdout)['configured'] == 'Good Company Demo Club'
        result = subprocess.run([str(cli), 'queue'], input='{}', cwd=target, env=env,
                                check=True, capture_output=True, text=True)
        assert json.loads(result.stdout) == []
    print('Installed CLI smoke check passed outside the source checkout.')


if __name__ == '__main__':
    main()
