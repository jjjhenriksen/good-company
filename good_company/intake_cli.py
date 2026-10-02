"""Owner-only Gmail confirmation issuance and exact-message intake."""
import argparse
import json
import os
from pathlib import Path
import sqlite3

from .google_intake import GoogleReplyProvider
from .intake import dispatch
from .latch import LatchMCP, LatchOperations
from .onboarding import SetupCoordinator
from .providers import ProviderError


def main():
    parser = argparse.ArgumentParser(description='Confirm enrolled participant actions through the existing Gmail connection')
    parser.add_argument('--config', required=True, type=Path)
    commands = parser.add_subparsers(dest='action', required=True)
    issue = commands.add_parser('issue', help='Owner-authorized email to one enrolled participant; consumes the shared budget')
    issue.add_argument('--recipient', required=True)
    issue.add_argument('--command', required=True, help='STOP, DECLINE/COMPLETE assignment-id, or SIGNUP/ACCEPT/DECLINE-OFFER task-id')
    issue.add_argument('--operation-id', required=True)
    issue.add_argument('--authority', required=True)
    reconcile = commands.add_parser('reconcile', help='Poll existing issuance; never resend')
    reconcile.add_argument('--operation-id', required=True)
    receive = commands.add_parser('receive', help='Read one exact Gmail message ID; no mailbox scan')
    receive.add_argument('--message-id', required=True)
    args = parser.parse_args()
    c = operations = None
    try:
        with args.config.open('rb') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError()
        config = json.loads(raw)
        if not isinstance(config, dict) or set(config) - {'db', 'journal', 'account', 'scopes', 'send_authority', 'unattended'}:
            raise ValueError()
        def path(key):
            value = Path(config[key])
            return value if value.is_absolute() else args.config.resolve().parent / value
        if path('db').resolve() == path('journal').resolve():
            raise ValueError()
        c = SetupCoordinator(path('db'))
        remit = c.autonomy()
        if not remit or config['account'] != remit['sender']:
            raise ProviderError('reply_account_outside_remit')
        if args.action == 'issue' and (not remit['enabled'] or config.get('unattended') is not True
                                       or not config.get('send_authority')):
            raise ProviderError('verification_send_outside_remit')
        operations = LatchOperations(path('journal'),
            LatchMCP(os.environ.get('PLOW_API_BASE'), os.environ.get('PLOW_AGENT_TOKEN')))
        provider = GoogleReplyProvider(operations, config['account'], config['scopes'], 'participant-intake',
            coordinator=c, timezone=c.profile()['timezone'],
            send_authority=config.get('send_authority'), unattended=config.get('unattended', False))
        if args.action == 'issue':
            result = provider.issue(args.recipient, args.command, args.operation_id, args.authority)
        elif args.action == 'reconcile':
            result = provider.reconcile_challenge(args.operation_id)
        else:
            result = dispatch(c, provider, args.message_id)
        print(json.dumps(result))
        return 2 if result.get('status') in ('issuing', 'unknown', 'failed') else 0
    except ProviderError as error:
        print(json.dumps({'status': 'blocked', 'reason': str(error)}))
        return 2
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error):
        print(json.dumps({'status': 'error', 'reason': 'intake_configuration_or_execution_failed'}))
        return 2
    finally:
        if operations:
            operations.close()
        if c:
            c.db.close()


if __name__ == '__main__':
    raise SystemExit(main())
