"""JSON-in/JSON-out tools the OpenClaw skill can invoke without shell interpolation."""
import argparse
import json
import os
import sys
from pathlib import Path
from .core import digest
from .core import Coordinator


def main():
    parser = argparse.ArgumentParser(description='Good Company coordination tools')
    parser.add_argument('--db', default=os.environ.get('GOOD_COMPANY_DB', '.state/good-company.sqlite'))
    parser.add_argument('action', choices=['configure', 'ingest', 'retrieve'])
    parser.add_argument('--input', type=Path, help='JSON request file; defaults to stdin, or {} when terminal')
    args = parser.parse_args()
    try:
        request = json.loads(args.input.read_text() if args.input else ('{}' if sys.stdin.isatty() else sys.stdin.read() or '{}'))
        coordinator = Coordinator(args.db)
        if args.action == 'review':
            result = coordinator.reminder(request['rid'])
            result['review_hash'] = digest(result['message'])
        else:
            # No simulated clock in the public CLI; tests call the library directly.
            if 'now' in request:
                raise ValueError('The CLI uses the real clock. Simulated times are for library tests only.')
            action = args.action.replace('-', '_')
            result = getattr(coordinator, action)(**request)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
