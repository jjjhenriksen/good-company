"""Owner-only scheduler entrypoint; configuration never contains credentials."""
import argparse
import json
import os
from pathlib import Path
import sqlite3

from .cycle import run_cycle
from .google_mail import GoogleProvider
from .latch import LatchMCP, LatchOperations
from .modules import ModuleCoordinator as SetupCoordinator


def main():
    parser = argparse.ArgumentParser(description='Run one authorized Good Company delivery cycle')
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--cycle-id', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    args = parser.parse_args()
    coordinator = operations = None
    try:
        with args.config.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError('oversized config')
        config = json.loads(raw)
        if not isinstance(config, dict) or set(config) - {'db', 'journal', 'account', 'scopes', 'send_authority', 'unattended'}:
            raise ValueError('invalid config')

        def state_path(name):
            value = Path(config[name])
            return value if value.is_absolute() else args.config.resolve().parent / value

        if state_path('db').resolve() == state_path('journal').resolve():
            raise ValueError('separate operation journal required')
        coordinator = SetupCoordinator(state_path('db'))
        policy = coordinator.autonomy()
        if not policy or not policy.get('enabled'):
            print(json.dumps({'status': 'paused', 'cycle_id': args.cycle_id}))
            return 0
        # Provider discovery must not precede the owner's explicit permission.
        if config.get('unattended') is not True or not config.get('send_authority'):
            print(json.dumps({'status': 'blocked', 'reason': 'unattended_sender_permission_unverified'}))
            return 2
        operations = LatchOperations(state_path('journal'),
            LatchMCP(os.environ.get('PLOW_API_BASE'), os.environ.get('PLOW_AGENT_TOKEN')))
        provider = GoogleProvider(operations, config['account'], config['scopes'], args.cycle_id,
            timezone=coordinator.profile()['timezone'], send_authority=config['send_authority'], unattended=True)
        result = run_cycle(coordinator, provider, args.cycle_id, args.start, args.end)
        print(json.dumps(result))
        return 0 if result['status'] in ('completed', 'paused', 'already_running') else 2
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error):
        print(json.dumps({'status': 'error', 'reason': 'cycle_configuration_or_execution_failed'}))
        return 2
    finally:
        if operations:
            operations.close()
        if coordinator:
            coordinator.db.close()


if __name__ == '__main__':
    raise SystemExit(main())
