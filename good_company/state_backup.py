"""Private offline state snapshots. Includes install identity and delivery history."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile


def private_destination(path):
    path = Path(path).absolute()
    path = path.parent.resolve() / path.name
    if path.exists() or path.is_symlink():
        raise ValueError('Destination must not exist; never overwrite active state.')
    if 'outputs' in path.parts or any((parent / '.git').exists() for parent in path.parents):
        raise ValueError('Keep private backups outside repositories and public output folders.')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def checksum(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_state(source, destination, offline=False):
    if offline is not True:
        raise ValueError('Stop the runtime and scheduler, then explicitly confirm offline=True.')
    source = Path(source).resolve(strict=True)
    destination = private_destination(destination)
    if not source.is_dir() or destination.is_relative_to(source):
        raise ValueError('Use a state directory and an external backup destination.')
    with tempfile.TemporaryDirectory(prefix='.state-backup-', dir=destination.parent) as temporary:
        root = Path(temporary) / 'snapshot'
        root.mkdir(mode=0o700)
        manifest = {'format': 2, 'files': {}, 'modes': {}, 'directories': []}
        for item in sorted(source.rglob('*')):
            if item.is_symlink():
                raise ValueError('State contains symlinks; resolve and review them before backup.')
            relative = item.relative_to(source)
            if relative.as_posix() == 'backup-manifest.json':
                raise ValueError('State uses the reserved backup manifest name.')
            target = root / relative
            if item.is_dir():
                target.mkdir(mode=0o700, exist_ok=True)
                manifest['directories'].append(relative.as_posix())
                continue
            if not item.is_file():
                raise ValueError('State contains a non-regular file; stop services and review it.')
            if item.name.endswith(('-wal', '-shm')):
                owner = item.with_name(item.name[:-4])
                if owner.is_file() and not owner.is_symlink():
                    with owner.open('rb') as stream:
                        if stream.read(16) == b'SQLite format 3\x00':
                            continue
            with item.open('rb') as stream:
                sqlite_file = stream.read(16) == b'SQLite format 3\x00'
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if sqlite_file:
                original = sqlite3.connect(item.as_uri() + '?mode=ro', uri=True)
                copied = sqlite3.connect(target)
                try:
                    original.backup(copied)
                    if copied.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Database snapshot failed integrity verification.')
                finally:
                    copied.close(); original.close()
            else:
                shutil.copyfile(item, target)
            mode = 0o600 | (item.stat().st_mode & 0o100)
            target.chmod(mode)
            manifest['modes'][relative.as_posix()] = mode
            manifest['files'][relative.as_posix()] = checksum(target)
        record = root / 'backup-manifest.json'
        record.write_text(json.dumps(manifest, indent=2))
        record.chmod(0o600)
        os.rename(root, destination)
    return {'files': len(manifest['files']), 'scope': 'Private offline state including credentials/identity when present; never publish this directory.'}


def restore_state(backup, destination, offline=False):
    if offline is not True:
        raise ValueError('Stop the runtime and scheduler before restoring.')
    root = Path(backup).resolve(strict=True)
    destination = private_destination(destination)
    manifest = json.loads((root / 'backup-manifest.json').read_text())
    if manifest.get('format') not in (1, 2) or not isinstance(manifest.get('files'), dict):
        raise ValueError('Unsupported backup manifest.')
    directories = manifest.get('directories') if manifest['format'] == 2 else []
    if not isinstance(directories, list) or any(not isinstance(name, str) for name in directories):
        raise ValueError('Unsupported backup directory records.')
    if len(directories) != len(set(directories)):
        raise ValueError('Duplicate backup directory records.')
    for name in directories:
        relative = Path(name)
        source = root / relative
        if (not name or relative == Path('.') or relative.is_absolute() or '..' in relative.parts
                or name == 'backup-manifest.json' or not source.is_dir()
                or any(p.is_symlink() for p in [source, *source.parents] if p != root.parent)):
            raise ValueError('Unsafe backup directory path.')
    for name, expected in manifest['files'].items():
        relative = Path(name)
        source = root / relative
        if relative.is_absolute() or '..' in relative.parts or not source.is_file() or any(p.is_symlink() for p in [source, *source.parents] if p != root.parent):
            raise ValueError('Unsafe backup path.')
        if manifest.get('modes', {}).get(name, 0o600) not in (0o600, 0o700):
            raise ValueError('Unsafe backup file mode.')
        if checksum(source) != expected:
            raise ValueError('Backup checksum mismatch; prior state was preserved.')
    with tempfile.TemporaryDirectory(prefix='.state-restore-', dir=destination.parent) as temporary:
        restored = Path(temporary) / 'state'
        restored.mkdir(mode=0o700)
        for name in sorted(directories):
            (restored / name).mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in manifest['files']:
            target = restored / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(root / name, target)
            target.chmod(manifest.get('modes', {}).get(name, 0o600))
        for directory in restored.rglob('*'):
            if directory.is_dir():
                directory.chmod(0o700)
        os.rename(restored, destination)
    return {'restored': True, 'files': len(manifest['files']), 'next': 'Verify identity, policy and receipts before starting one scheduler.'}
