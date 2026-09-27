"""Owner-only, read-only Google availability check through the existing Latch path."""
import argparse
import json
import os
from pathlib import Path
import sqlite3

from .google_calendar import GoogleCalendar
from .latch import LatchMCP, LatchOperations
from .providers import ProviderError


def main():
    parser = argparse.ArgumentParser(description='Check one selected calendar without reading event titles')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--check-id', required=True)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    args = parser.parse_args()
    operations = None
    try:
        with args.config.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('oversized config')
        config = json.loads(raw)
        if not isinstance(config, dict) or set(config) != {'journal', 'account', 'scopes'}:
            raise ValueError('invalid config')
        if not isinstance(config['scopes'], dict) or args.scope not in config['scopes']:
            raise ProviderError('google_calendar_outside_scope')
        journal = Path(config['journal'])
        if not journal.is_absolute():
            journal = args.config.resolve().parent / journal
        operations = LatchOperations(journal,
            LatchMCP(os.environ.get('PLOW_API_BASE'), os.environ.get('PLOW_AGENT_TOKEN')))
        provider = GoogleCalendar(operations, config['account'], config['scopes'], args.check_id)
        print(json.dumps(provider.check_availability(args.scope, args.start, args.end)))
        return 0
    except ProviderError as error:
        print(json.dumps({'status': 'unavailable', 'reason': str(error)}))
        return 2
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error):
        print(json.dumps({'status': 'unavailable', 'reason': 'availability_configuration_or_read_failed'}))
        return 2
    finally:
        if operations:
            operations.close()


if __name__ == '__main__':
    raise SystemExit(main())
