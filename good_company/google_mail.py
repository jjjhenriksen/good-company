"""Google mail delivery with durable per-recipient reconciliation through Latch."""
from dataclasses import replace
import hashlib
import json
import re

from .google_calendar import GoogleCalendar
from .providers import ProviderError, SendResult


class GoogleProvider(GoogleCalendar):
    """Calendar plus mail. An owner authority reference is required to send.

    unattended is an operator attestation, not something account discovery proves.
    Leave it false until permissions have been observed in the deployed context.
    Latch remains the authority for every actual tool invocation.
    """
    def __init__(self, *args, send_authority=None, unattended=False, **kwargs):
        super().__init__(*args, **kwargs)
        if type(unattended) is not bool:
            raise ProviderError('invalid_unattended_attestation')
        if send_authority is not None and (not isinstance(send_authority, str) or not send_authority.strip()):
            raise ProviderError('invalid_send_authority')
        self.send_authority, self.unattended = send_authority, unattended
        self.operations.db.execute('''CREATE TABLE IF NOT EXISTS google_mail_groups(
            id TEXT PRIMARY KEY, account TEXT NOT NULL, fingerprint TEXT NOT NULL,
            authority TEXT NOT NULL, children TEXT NOT NULL)''')
        self.operations.db.commit()

    def account(self):
        return replace(super().account(), unattended_send=bool(self.send_authority and self.unattended),
                       reconcile_send=True)

    def _group(self, operation_id):
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ProviderError('missing_mail_operation')
        return 'google-mail:' + hashlib.sha256(json.dumps([self.email, operation_id]).encode()).hexdigest()

    def _batches(self, message):
        if not isinstance(message, dict) or message.get('sender') != self.email:
            raise ProviderError('mail_sender_mismatch')
        if message.get('missing'):
            raise ProviderError('mail_missing_requirements')
        # No hidden transport instructions or unsupported attachments/headers.
        if set(message) - {'sender', 'to', 'bcc', 'subject', 'body', 'audience', 'missing', 'sources'}:
            raise ProviderError('unsupported_mail_fields')
        for key in ('subject', 'body'):
            if not isinstance(message.get(key), str) or not message[key].strip() or '\x00' in message[key]:
                raise ProviderError('invalid_mail_content')
        if any(c in message['subject'] for c in '\r\n'):
            raise ProviderError('invalid_mail_subject')
        for key in ('to', 'bcc'):
            if not isinstance(message.get(key), list) or any(
                not isinstance(a, str) or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', a)
                or a.startswith('-') for a in message[key]):
                raise ProviderError('invalid_mail_recipients')
        addresses = message['to'] + message['bcc']
        if not addresses or len(addresses) > 100 or len({a.casefold() for a in addresses}) != len(addresses):
            raise ProviderError('invalid_mail_recipient_count')
        # gog requires To. Individual copies keep BCC-only recipients hidden
        # from one another and do not add an unapproved owner/self recipient.
        return [(message['to'], message['bcc'])] if message['to'] else [([a], []) for a in message['bcc']]

    def send(self, message, operation_id, idempotency_key=None):
        if not self.send_authority:
            raise ProviderError('mail_authority_required')
        if idempotency_key is not None:
            raise ProviderError('google_idempotency_not_supported')
        batches = self._batches(message)
        group = self._group(operation_id)
        fingerprint = hashlib.sha256(json.dumps(message, sort_keys=True).encode()).hexdigest()
        children = [group + ':' + str(i) for i in range(len(batches))]
        db = self.operations.db
        with db:
            inserted = db.execute('INSERT OR IGNORE INTO google_mail_groups VALUES(?,?,?,?,?)',
                (group, self.email, fingerprint, self.send_authority, json.dumps(children))).rowcount
        row = db.execute('SELECT * FROM google_mail_groups WHERE id=?', (group,)).fetchone()
        if row['fingerprint'] != fingerprint or row['account'] != self.email:
            raise ProviderError('mail_operation_payload_changed')
        if inserted:
            for child, (to, bcc) in zip(children, batches):
                argv = ['plow-gog', 'gmail', 'send', '--account=' + self.email,
                        '--to=' + ','.join(to), '--subject=' + message['subject'], '--body=' + message['body'], '--json']
                if bcc:
                    argv += ['--bcc=' + ','.join(bcc)]
                result = self.operations.execute(child, argv, 'Deliver the owner-authorized Good Company notice to its approved recipients.')
                if result['state'] in ('denied', 'blocked'):
                    break
        return self._outcome(group, poll=False)

    def reconcile(self, operation_id):
        # Deliberately never calls execute. Missing child handles stay unknown.
        return self._outcome(self._group(operation_id), poll=True)

    def _outcome(self, group, poll):
        row = self.operations.db.execute('SELECT * FROM google_mail_groups WHERE id=? AND account=?', (group, self.email)).fetchone()
        if not row:
            raise ProviderError('unknown_google_mail_operation')
        receipts, states = [], []
        for child in json.loads(row['children']):
            try:
                result = self.operations.poll(child) if poll else self.operations.status(child)
            except ProviderError:
                result = {'state': 'uncertain'}
            states.append(result['state'])
            payload = result.get('result') or {}
            if result['state'] != 'completed' or type(payload.get('exit_code')) is not int or payload['exit_code'] != 0:
                continue
            output = payload.get('output', '')
            prefix = 'Note: Using direct access token (expires in ~1 hour; no auto-refresh)\n'
            if isinstance(output, str) and output.startswith(prefix):
                output = output[len(prefix):]
            try:
                data = json.loads(output)
            except (ValueError, TypeError):
                continue
            if not isinstance(data, dict):
                continue
            message_id, thread_id = data.get('messageId'), data.get('threadId')
            if all(isinstance(v, str) and re.fullmatch('[0-9a-fA-F]+', v) for v in (message_id, thread_id)):
                receipts.append(message_id)
        if len(receipts) == len(states) and len(set(receipts)) == len(receipts):
            return SendResult('accepted', 'gmail:' + ','.join(receipts))
        if len(states) == 1 and states[0] in ('denied', 'blocked'):
            return SendResult('failed', states[0] + ':' + group)
        # Nonzero exits, incomplete groups and ambiguous results may follow an
        # actual send. Keep every accepted child in the journal; never resend.
        return SendResult('unknown', 'unconfirmed:' + group)
