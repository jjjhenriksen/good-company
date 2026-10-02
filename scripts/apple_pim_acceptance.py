#!/usr/bin/env python3
"""Repeat isolated native Apple PIM reads, containment and restart checks; never send mail."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from good_company.local_sandbox import initialize


def request(port, token, route, payload=None):
    # Deliberately no remote URL, redirects, proxy or arbitrary tool arguments.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)
    req = urllib.request.Request(f'http://127.0.0.1:{port}/{route}',
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
        data=None if payload is None else json.dumps(payload).encode())
    try:
        response = opener.open(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError('Response limit exceeded')
        return response.code, json.loads(raw)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def snapshot(state):
    config = json.loads((state / 'openclaw.json').read_text())
    # Read the SQLite database independently, without bootstrapping or migrations.
    with closing(sqlite3.connect((state / 'state.sqlite').as_uri() + '?mode=ro', uri=True)) as db:
        settings = dict(db.execute("SELECT key,value FROM settings WHERE key IN ('profile','autonomy')"))
        counts = {table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                  for table in ('events', 'reminders', 'task_notices')}
    return {'settings': settings, 'counts': counts,
            'token_hash': hashlib.sha256(config['gateway']['auth']['token'].encode()).hexdigest()}


def empty_paused(value):
    return (json.loads(value['settings']['autonomy'])['enabled'] is False
            and all(n == 0 for n in value['counts'].values()))


def blocked(status, body):
    # A schema error, absent tool, approval request or success is not guard proof.
    return status == 403 and body.get('error', {}).get('type') == 'tool_call_blocked'


def empty_calendar_result(status, body):
    result = body.get('result', {})
    if (status != 200 or body.get('ok') is not True or result.get('isError')
            or result.get('details') != {'domain': 'calendar', 'action': 'list'}):
        return False
    blocks = result.get('content', [])
    if len(blocks) != 1 or blocks[0].get('type') != 'text':
        return False
    text = blocks[0].get('text', '')
    # The plugin prepends its datamarking preamble to one JSON value. Discard
    # only that known preamble; never search arbitrary prose for a success flag.
    if text.startswith('Data between [UNTRUSTED_CALENDAR_DATA_'):
        _, separator, text = text.partition('\n\n')
        if not separator:
            return False
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return False
    return isinstance(value, dict) and value.get('success') is True and value.get('calendars') == []


def probe(port, token, state):
    def invoke(tool, args):
        return request(port, token, 'tools/invoke', {'tool': tool, 'args': args})
    checks = {}
    status, body = invoke('apple_pim_calendar', {'action': 'list'})
    checks['native_calendar_empty_allowlist'] = empty_calendar_result(status, body)
    status, _ = invoke('apple_pim_mail', {'action': 'accounts'})
    checks['mail_tool_unavailable'] = status == 404
    # A deliberately nonexistent calendar makes this probe non-writing even if
    # the guard regresses. It must return the guard's exact denial, not CLI failure.
    status, body = invoke('apple_pim_calendar', {'action': 'create',
        'calendarId': 'good-company-nonexistent-6a3286b8-2c16-4d64-9e9c-f87c34117e1f',
        'title': 'Fictional containment probe', 'startDate': '2030-01-01T10:00:00Z',
        'endDate': '2030-01-01T11:00:00Z'})
    checks['calendar_mutation_blocked'] = blocked(status, body)
    status, body = invoke('apple_pim_calendar', {'action': 'list', 'configDir': str(state / 'nonexistent-scope')})
    checks['scope_override_blocked'] = blocked(status, body)
    return checks


def stop(process):
    # Only the process group created by this harness, never another gateway.
    if process is not None and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            process.wait(timeout=5)
            return
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def start(state, port, token, log, seconds):
    process = subprocess.Popen([str(state / 'start.sh')], stdout=log, stderr=log,
                               start_new_session=True)
    try:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Gateway exited')
            try:
                health, _ = request(port, token, 'healthz')
                ready, _ = request(port, token, 'readyz')
                if health == ready == 200:
                    return process
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        raise TimeoutError('Startup deadline exceeded')
    except BaseException:
        stop(process)
        raise


def run(state, plugin, launcher, node, bin_dir, port, startup_seconds=60):
    report = {'evidence_kind': 'isolated_native_runtime', 'live_provider_acceptance': False,
              'remaining_issue_acceptance': False, 'checks': {}, 'passed': False}
    state = Path(state).expanduser().resolve()
    process, created = None, False
    try:
        # Refuse occupied ports before creating state or contacting any runtime.
        with socket.socket() as check:
            check.bind(('127.0.0.1', port))
        initialize(state, ROOT, plugin, launcher, node, bin_dir, port)
        created = True
        token = json.loads((state / 'openclaw.json').read_text())['gateway']['auth']['token']
        before = snapshot(state)
        report['checks']['initial_ledger_empty_paused'] = empty_paused(before)
        with os.fdopen(os.open(state / 'gateway-private.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as log:
            process = start(state, port, token, log, startup_seconds)
            report['checks']['health_and_readiness'] = True
            report['checks'].update(probe(port, token, state))
            stop(process)
            process = None
            process = start(state, port, token, log, startup_seconds)
            report['checks']['restart_health_and_readiness'] = True
            report['checks'].update({'restart_' + name: value for name, value in probe(port, token, state).items()})
            after = snapshot(state)
            report['checks']['settings_token_and_ledger_preserved'] = before == after and empty_paused(after)
        report['passed'] = all(report['checks'].values())
    except Exception as error:
        # Never serialize native output, tokens, message bodies or exception text.
        report['failure_class'] = type(error).__name__
    finally:
        stop(process)
    if created:
        with os.fdopen(os.open(state / 'native-report.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
            json.dump(report, output, indent=2)
            output.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('state', 'plugin', 'launcher', 'node', 'bin-dir'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--port', type=int, default=19846)
    parser.add_argument('--startup-seconds', type=int, default=60, choices=range(1, 121))
    args = parser.parse_args()
    report = run(args.state, args.plugin, args.launcher, args.node, args.bin_dir,
                 args.port, args.startup_seconds)
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
