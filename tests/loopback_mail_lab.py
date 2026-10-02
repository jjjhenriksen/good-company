"""Private .invalid-only HTTP lab. Its receipts prove local acceptance, not email delivery."""
from dataclasses import replace
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
import threading
import urllib.request
from uuid import uuid4

from good_company.apple_pim import NativeApplePIM
from good_company.core import digest
from good_company.core import stamp
from good_company.intake import ApplePIMIntake
from good_company.providers import ProviderError, SendResult


class MailLab:
    def __init__(self, root, owner='coordinator@example.invalid', calendars=None):
        self.root = Path(root).resolve()
        if not owner.endswith('@example.invalid'):
            raise ValueError('Fictional owner required')
        self.owner = owner
        self.calendars = calendars or {}
        self.credentials = {name: secrets.token_urlsafe(24) for name in ('owner', 'alex', 'sam', 'lee', 'pat')}
        self.policy_path = self.root / 'lab-trusted-senders.json'
        self.policy_path.write_text(json.dumps({'trustedAuthservIds': {'lab-account': ['lab.example.invalid']},
            'trustedSenders': [{'emails': [name + '@example.invalid'], 'expectedDkimDomains': ['example.invalid']}
                               for name in ('alex', 'sam', 'lee', 'pat')]}))
        self.policy_path.chmod(0o600)
        self.db = sqlite3.connect(self.root / 'mail-lab.sqlite', check_same_thread=False)
        (self.root / 'mail-lab.sqlite').chmod(0o600)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS inbox(
            id TEXT PRIMARY KEY, principal TEXT NOT NULL, message TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS accepted(
            operation TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, receipt TEXT NOT NULL,
            recipients TEXT NOT NULL);''')
        self.lock = threading.RLock()
        self.server = None

    def __enter__(self):
        lab = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    token = self.headers.get('Authorization', '').removeprefix('Bearer ')
                    principal = next((name for name, secret in lab.credentials.items()
                                      if secrets.compare_digest(token, secret)), None)
                    if principal is None:
                        raise PermissionError()
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 100_000:
                        raise ValueError()
                    payload = json.loads(self.rfile.read(size))
                    with lab.lock:
                        value = lab.handle(self.path, principal, payload)
                    raw = json.dumps(value).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                except PermissionError:
                    self.send_error(403, 'lab_permission_denied')
                except (ValueError, KeyError, TypeError, sqlite3.IntegrityError):
                    self.send_error(400, 'lab_request_rejected')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.db.close()

    def request(self, path, payload, principal='owner', token=None):
        request = urllib.request.Request(f'http://127.0.0.1:{self.port}' + path,
            data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' +
            (token if token is not None else self.credentials[principal]), 'Content-Type': 'application/json'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=5) as response:
            return json.loads(response.read(100_001))

    def submit(self, person, command, claimed_sender=None):
        return self.request('/submit', {'command': command,
            'sender': claimed_sender or person + '@example.invalid'}, principal=person)['id']

    def handle(self, path, principal, payload):
        if path == '/submit':
            if principal == 'owner':
                raise PermissionError()
            content, sender = payload['command'], payload['sender']
            if not isinstance(content, str) or len(content) > 4096 or not isinstance(sender, str):
                raise ValueError()
            mid = uuid4().hex + '@example.invalid'
            msg = {'messageId': mid, 'senderAddress': sender, 'account': 'Isolated mail lab',
                   'mailbox': 'INBOX', 'content': content,
                   'allHeaders': 'Lab credential transport; this is not DKIM evidence'}
            with self.db:
                self.db.execute('INSERT INTO inbox VALUES(?,?,?)', (mid, principal + '@example.invalid', json.dumps(msg)))
            return {'id': mid}
        if principal != 'owner':
            raise PermissionError()
        if path == '/tools/invoke':
            args = payload['args']
            if args['configDir'] != str(self.root):
                raise PermissionError()
            action = args['action']
            if payload['tool'] == 'apple_pim_calendar':
                if action == 'list':
                    value = {'success': True, 'calendars': [{'id': cid} for cid in self.calendars]}
                elif action == 'events' and args.get('calendar') in self.calendars:
                    first, last = stamp(args['from']), stamp(args['to'])
                    if first >= last or type(args.get('limit')) is not int or args['limit'] != 10001:
                        raise ValueError()
                    records = [e for e in self.calendars[args['calendar']]
                               if stamp(e['startDate']) < last and stamp(e['endDate']) > first]
                    value = {'success': True, 'events': records[:args['limit']], 'count': min(len(records), args['limit'])}
                else:
                    raise PermissionError()
                return {'ok': True, 'result': {'details': {'domain': 'calendar', 'action': action},
                        'content': [{'type': 'text', 'text': json.dumps(value)}]}}
            if payload['tool'] != 'apple_pim_mail':
                raise PermissionError()
            if action == 'accounts':
                value = {'success': True, 'accounts': [{'id': 'lab-account', 'name': 'Isolated mail lab',
                          'enabled': True, 'userName': self.owner}]}
            elif action in ('get', 'auth_check'):
                if args['account'] != 'lab-account' or args['mailbox'] != 'INBOX':
                    raise PermissionError()
                row = self.db.execute('SELECT principal,message FROM inbox WHERE id=?', (args['id'],)).fetchone()
                if row is None:
                    raise ValueError()
                sender, msg = row[0], json.loads(row[1])
                if action == 'get':
                    value = {'success': True, 'message': msg}
                else:
                    if args['trustedSenders'] != str(self.policy_path):
                        raise PermissionError()
                    verified = sender == msg['senderAddress'].casefold()
                    value = {'evaluated': True, 'verdict': 'verified' if verified else 'rejected', 'sender': sender,
                        'checks': {'dkim': {'result': 'pass' if verified else 'fail', 'match': verified,
                                           'expected': ['example.invalid']}},
                        'messageBinding': {'messageId': args['id'], 'accountId': 'lab-account', 'mailbox': 'INBOX',
                            'senderAddress': sender, 'contentSha256': hashlib.sha256(msg['content'].encode()).hexdigest(),
                            'headersSha256': hashlib.sha256(msg['allHeaders'].encode()).hexdigest(),
                            'policySha256': hashlib.sha256(self.policy_path.read_bytes()).hexdigest()}}
            else:
                raise PermissionError()
            return {'ok': True, 'result': {'details': {'domain': 'mail', 'action': action},
                    'content': [{'type': 'text', 'text': json.dumps(value)}]}}
        if path == '/send':
            msg, operation = payload['message'], payload['operation']
            recipients = msg.get('to', []) + msg.get('bcc', [])
            allowed = {name + '@example.invalid' for name in ('alex', 'sam', 'lee', 'pat')}
            if (msg.get('sender') != self.owner or not recipients or not set(recipients) <= allowed
                    or payload.get('key') != operation or not isinstance(operation, str) or not operation):
                raise PermissionError()
            fingerprint = digest(msg)
            previous = self.db.execute('SELECT payload_hash,receipt FROM accepted WHERE operation=?', (operation,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise ValueError()
                return {'outcome': 'accepted', 'reference': previous[1]}
            receipt = 'loopback-lab:' + uuid4().hex
            with self.db:
                self.db.execute('INSERT INTO accepted VALUES(?,?,?,?)',
                                (operation, fingerprint, receipt, json.dumps(recipients)))
            return {'outcome': 'accepted', 'reference': receipt}
        if path == '/reconcile':
            row = self.db.execute('SELECT receipt FROM accepted WHERE operation=?', (payload['operation'],)).fetchone()
            return {'outcome': 'accepted', 'reference': row[0]} if row else {'outcome': 'unknown', 'reference': 'lab-no-record'}
        raise PermissionError()

    def accepted(self):
        with self.lock:
            return [{'operation': row[0], 'receipt': row[1], 'recipients': json.loads(row[2])}
                    for row in self.db.execute('SELECT operation,receipt,recipients FROM accepted ORDER BY rowid')]

    def provider(self):
        return LabProvider(self)


class LabProvider(ApplePIMIntake):
    def __init__(self, lab):
        self.lab = lab
        super().__init__(NativeApplePIM(lab.port, lab.credentials['owner'], lab.root),
                         'lab-account', lab.owner, 'INBOX', lab.policy_path)

    def account(self):
        return replace(super().account(), provider='isolated-loopback-lab',
                       unattended_send=True, idempotent_send=True, reconcile_send=True)

    def send(self, message, operation_id, idempotency_key):
        try:
            return SendResult(**self.lab.request('/send', {'message': message, 'operation': operation_id, 'key': idempotency_key}))
        except Exception:
            raise ProviderError('lab_send_unconfirmed') from None

    def reconcile(self, operation_id):
        try:
            return SendResult(**self.lab.request('/reconcile', {'operation': operation_id}))
        except Exception:
            raise ProviderError('lab_reconcile_unconfirmed') from None
