"""Refuse to discard an old ledger when upgrading the volume layout."""
import os
from pathlib import Path
import sys


def check_ledger_migration(old, current):
    if old.is_file() and old.stat().st_size and (not current.is_file() or not current.stat().st_size):
        raise RuntimeError('Existing coordination state requires offline migration. Follow INSTALL.md before starting; the old ledger has been retained.')


def main():
    try:
        check_ledger_migration(Path('/var/lib/plow/good-company/state.sqlite'), Path('/var/lib/good-company/state.sqlite'))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 78
    os.execvp('node', ['node', '/opt/plow/boot/main.js'])


if __name__ == '__main__':
    sys.exit(main())
