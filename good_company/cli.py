"""JSON-in/JSON-out tools the OpenClaw skill can invoke without shell interpolation."""
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from .core import digest
from .validation import MAX_REQUEST_BYTES, RequestError, validate_request, safe_error
from .corrections import CorrectionCoordinator as Coordinator


def main():
    parser = argparse.ArgumentParser(description='Good Company coordination tools')
    parser.add_argument('--db', default=os.environ.get('GOOD_COMPANY_DB', '.state/good-company.sqlite'))
    parser.add_argument('action', choices=['withdraw-source', 'create-correction', 'correction-queue', 'correction-claim', 'correction-receipt', 'task-impacts', 'communication-budget', 'set-contact-preferences', 'set-contact-consent', 'configure', 'ingest', 'retrieve', 'import-calendar', 'events',
                                         'plan', 'queue', 'review', 'edit', 'approve', 'claim', 'receipt', 'conflicts',
                                         'set-dress-code', 'dress-code', 'configure-autonomy', 'autonomy',
                                         'set-volunteer', 'add-task', 'delegate', 'task-queue', 'task-claim',
                                         'task-receipt', 'decline-task', 'close-task'])
    parser.add_argument('--input', type=Path, help='JSON request file; defaults to stdin, or {} when terminal')
    args = parser.parse_args()
    coordinator = None
    request = {}
    try:
        if args.input:
            with args.input.open('rb') as stream:
                raw = stream.read(MAX_REQUEST_BYTES + 1)
        else:
            raw = b'{}' if sys.stdin.isatty() else sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1) or b'{}'
        if len(raw) > MAX_REQUEST_BYTES:
            raise RequestError('Request exceeds the 2 MB limit.')
        request = json.loads(raw)
        validate_request(request)
        if not isinstance(request, dict):
            raise ValueError('Request must be a JSON object.')
        if 'now' in request:
            raise ValueError('The CLI uses the real clock. Simulated times are for library tests only.')
        coordinator = Coordinator(args.db)
        if args.action == 'review':
            result = coordinator.reminder(request['rid'])
            result['review_hash'] = digest(result['message'])
        else:
            action = args.action.replace('-', '_')
            result = getattr(coordinator, action)(**request)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, RecursionError) as error:
        print(json.dumps({'error': safe_error(error, request)}), file=sys.stderr)
        return 2
    finally:
        if coordinator is not None:
            coordinator.db.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
