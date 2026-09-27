#!/usr/bin/env python3
"""Exercise Docker's real ignore semantics using only fictional canary files."""
from pathlib import Path
import argparse
import subprocess
import tempfile


def main():
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ignore-file', type=Path, default=repo / '.dockerignore')
    args = parser.parse_args()
    # These must remain available to both runtime Dockerfiles. Check the actual
    # COPY sources against Git's tracked files, not just the ignore rules.
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=repo, text=True).splitlines())
    expected = {'Dockerfile', 'Dockerfile.arm64'}
    for dockerfile in ('Dockerfile', 'Dockerfile.arm64'):
        for line in (repo / dockerfile).read_text().splitlines():
            if not line.startswith('COPY ') or line.startswith('COPY --from='):
                continue
            source = line.split()[1]
            expected.update(name for name in tracked if name == source or (source.endswith('/') and name.startswith(source)))
    canaries = {'plow-credentials', '.env', 'personal-notes.md', 'unrelated/local.json'}
    # Test unexpected files beside every admitted source, including nested skill
    # and license directories. Test plausible source extensions as well.
    for parent in {str(Path(name).parent) for name in expected if '/' in name}:
        canaries.update(parent + '/private-canary.' + ext for ext in ('csv', 'env', 'txt', 'json', 'md', 'py'))
    with tempfile.TemporaryDirectory(prefix='good-company-context-') as temporary:
        root = Path(temporary)
        source, exported = root / 'input', root / 'exported'
        source.mkdir()
        (source / '.dockerignore').write_text(args.ignore_file.read_text())
        for name in expected | canaries:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('FICTIONAL_CANARY_NO_PRIVATE_DATA\n')
        # This scratch image does not execute anything or copy real repo content.
        (source / 'Dockerfile').write_text('FROM scratch\nCOPY . /context/\n')
        subprocess.run(['docker', 'build', '--output', 'type=local,dest=' + str(exported), str(source)],
                       check=True, stdout=subprocess.DEVNULL)
        actual = {str(path.relative_to(exported / 'context')) for path in (exported / 'context').rglob('*') if path.is_file()}
        if actual != expected:
            raise SystemExit('Build context mismatch: unexpected=' + repr(sorted(actual - expected))
                             + ', missing=' + repr(sorted(expected - actual)))
    print(f'Docker context admits {len(expected)} runtime files and excludes {len(canaries)} fictional private canaries.')


if __name__ == '__main__':
    main()
