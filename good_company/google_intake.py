"""Gmail reply intake using explicit, single-use mailbox possession challenges.

From and Authentication-Results are untrusted. Only a secret sent through the
existing accepted Google mail operation authorizes its preselected command.
This proves mailbox possession, not DKIM, authorship or the person's legal identity.
"""
import base64
from dataclasses import replace
from datetime import timedelta
from email import policy as email_policy
from email.parser import BytesParser
import hashlib
import json
import re
import secrets
from uuid import uuid4
from zoneinfo import ZoneInfo

from .core import digest, iso, required, stamp
from .google_calendar import GoogleCalendar
from .google_mail import GoogleProvider
from .intake import ApplePIMIntake
from .providers import ProviderError, authenticated_account
from .replies import VerifiedReply, _check_reply_account


class GoogleReplyProvider(GoogleProvider):
    def __init__(self, *args, coordinator, clock=stamp, **kwargs):
        super().__init__(*args, **kwargs)
        self.coordinator, self.clock = coordinator, clock
        coordinator.db.execute('''CREATE TABLE IF NOT EXISTS gmail_reply_challenges(
            id TEXT PRIMARY KEY, account TEXT NOT NULL, recipient TEXT NOT NULL,
            command TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
            expires TEXT NOT NULL, status TEXT NOT NULL, receipt TEXT,
            authority TEXT NOT NULL)''')
        coordinator.db.commit()

    def _fresh_reader(self):
        # Calendar refresh caching must never make a security recheck stale.
        return GoogleCalendar(self.operations, self.email, self.scopes,
                              'reply-observation:' + uuid4().hex, self.timezone)

    def account(self):
        return replace(self._fresh_reader().account(),
                       unattended_send=bool(self.send_authority and self.unattended),
                       reconcile_send=True)

    def _challenge_id(self, operation_id):
        required(operation_id, 'owner challenge operation ID')
        return digest([self.email, operation_id])

    @staticmethod
    def _status(row):
        return {'challenge_id': row['id'], 'status': row['status'],
                'expires_at': row['expires'], 'receipt': row['receipt']}

    def issue(self, recipient, command, operation_id, authority):
        """Owner-only issuance. Never triggered by an unverified incoming mail.

        The code is delivered only to the enrolled mailbox and is never returned.
        A claim precedes dispatch; interrupted issuance is reconciled, never resent.
        """
        required(authority, 'owner verification authority')
        if not isinstance(recipient, str):
            raise ProviderError('verification_recipient_required')
        ApplePIMIntake.command(command)  # fixed, bounded grammar; no free-form instructions
        key = self._challenge_id(operation_id)
        account = authenticated_account(self)
        c, now = self.coordinator, stamp(self.clock())
        _check_reply_account(c, account)
        token = secrets.token_hex(32)
        message = {'sender': self.email, 'to': [recipient], 'bcc': [],
                   'subject': 'Confirm your Good Company response',
                   'body': 'To confirm ' + command + ', reply with only this line within one hour:\n'
                           'GCVERIFY ' + token + '\n\nUse this code only if you want that action. Do not forward it.'}
        with c.db:
            c.db.execute('BEGIN IMMEDIATE')
            row = c.db.execute('SELECT * FROM gmail_reply_challenges WHERE id=?', (key,)).fetchone()
            if row:
                if (row['account'], row['recipient'], row['command'], row['authority']) != (
                        self.email, recipient.casefold(), command, authority):
                    raise ProviderError('verification_operation_changed')
                return self._status(row)
            remit = c.autonomy()
            if (not remit['enabled'] or not account.unattended_send
                    or self.email != remit['sender']
                    or recipient not in remit['allowed_recipients']):
                raise ProviderError('verification_send_outside_remit')
            roster = [json.loads(row[0]) for row in c.db.execute('SELECT payload FROM volunteers')]
            if len([v for v in roster if v['email'].casefold() == recipient.casefold()]) != 1:
                raise ProviderError('verification_recipient_not_enrolled')
            if not 7 <= now.astimezone(ZoneInfo(c.profile()['timezone'])).hour < 21:
                raise ProviderError('verification_quiet_hours')
            c._check_communication_budget(now)
            c._check_contacts(message, now)
            c._record_contacts('verification', key, message, now)
            c.log('email_verification_claim', key, {'authority': authority}, now)
            c.db.execute('INSERT INTO gmail_reply_challenges VALUES(?,?,?,?,?,?,?,?,?)',
                         (key, self.email, recipient.casefold(), command,
                          hashlib.sha256(token.encode()).hexdigest(), iso(now + timedelta(hours=1)),
                          'issuing', None, authority))
        try:
            result = self.send(message, 'verification:' + key)
        except Exception:
            # Provider output or exceptions can contain private mail or the code.
            raise ProviderError('verification_send_needs_reconciliation') from None
        return self._record_outcome(key, result)

    def reconcile_challenge(self, operation_id):
        key = self._challenge_id(operation_id)
        _check_reply_account(self.coordinator, authenticated_account(self))
        row = self.coordinator.db.execute('SELECT * FROM gmail_reply_challenges WHERE id=?', (key,)).fetchone()
        if not row:
            raise ProviderError('unknown_verification_operation')
        if row['status'] not in ('issuing', 'unknown'):
            return self._status(row)
        try:
            result = self.reconcile('verification:' + key)
        except ProviderError:
            raise ProviderError('verification_send_needs_owner_review') from None
        return self._record_outcome(key, result)

    def _record_outcome(self, key, result):
        status = {'accepted': 'active', 'failed': 'failed', 'unknown': 'unknown'}[result.outcome]
        with self.coordinator.db:
            # A late poll must never resurrect a consumed code.
            self.coordinator.db.execute('''UPDATE gmail_reply_challenges SET status=?,receipt=?
                WHERE id=? AND status IN ('issuing','unknown')''', (status, result.reference, key))
        return self._status(self.coordinator.db.execute(
            'SELECT * FROM gmail_reply_challenges WHERE id=?', (key,)).fetchone())

    def _message(self, message_id):
        data, _ = self._fresh_reader()._read(['plow-gog', 'gmail', 'get', message_id,
            '--account', self.email, '--format', 'raw', '--json'])
        msg = data.get('message')
        return self._confirmation(msg, message_id)

    @staticmethod
    def _confirmation(msg, message_id):
        if (not isinstance(msg, dict) or msg.get('id') != message_id
                or not isinstance(msg.get('labelIds'), list) or 'INBOX' not in msg['labelIds']):
            raise ProviderError('gmail_reply_outside_inbox')
        raw = GoogleCalendar._display_text(msg.get('raw'))
        if len(raw) > 180000 or not re.fullmatch(r'[A-Za-z0-9_-]+={0,2}', raw):
            raise ProviderError('gmail_reply_invalid_raw')
        try:
            content = base64.b64decode(raw + '=' * (-len(raw) % 4), altchars=b'-_', validate=True)
            mail = BytesParser(policy=email_policy.default).parsebytes(content)
            senders = mail.get_all('From', [])
            if len(senders) != 1 or senders[0].defects or len(senders[0].addresses) != 1:
                raise ValueError()
            sender = senders[0].addresses[0].addr_spec
            if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', sender):
                raise ValueError()
            parts = list(mail.walk())
            if any(part.defects or any(len(part.get_all(name, [])) > 1 for name in
                   ('Content-Type', 'Content-Transfer-Encoding', 'Content-Disposition')) for part in parts):
                raise ValueError()
            plain = [p for p in parts if p.get_content_type() == 'text/plain'
                     and p.get_content_disposition() != 'attachment' and not p.get_filename()]
            if len(plain) != 1 or any(p.get_content_type() == 'message/rfc822' for p in parts):
                raise ValueError()
            body = plain[0].get_content()
            if not isinstance(body, str) or len(body) > 4096:
                raise ValueError()
            # Mail.app can serialize a freshly composed confirmation as one
            # quoted line. A sole code is still explicit mailbox possession;
            # quoted history, multiple lines and extra instructions remain invalid.
            match = re.fullmatch(r'(?:> )?GCVERIFY ([0-9a-f]{64})', body.strip())
            if not match:
                raise ValueError()
        except (ValueError, TypeError, AttributeError, LookupError):
            raise ProviderError('gmail_reply_invalid_confirmation') from None
        return sender.casefold(), hashlib.sha256(match[1].encode()).hexdigest(), hashlib.sha256(content).hexdigest()

    def verified_reply(self, message_id):
        if not isinstance(message_id, str) or not re.fullmatch(r'[0-9a-fA-F]{1,64}', message_id):
            raise ProviderError('gmail_reply_invalid_message_id')
        before = authenticated_account(self)
        _check_reply_account(self.coordinator, before)
        first = self._message(message_id)
        if first != self._message(message_id) or before != authenticated_account(self):
            raise ProviderError('gmail_reply_changed_during_read')
        sender, token_hash, raw_hash = first
        db = self.coordinator.db
        with db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('''SELECT * FROM gmail_reply_challenges
                WHERE token_hash=? AND account=? AND recipient=? AND status='active' ''',
                             (token_hash, self.email, sender)).fetchone()
            if not row or stamp(row['expires']) <= stamp(self.clock()) or not row['receipt']:
                raise ProviderError('gmail_reply_proof_missing_expired_or_used')
            action, target = ApplePIMIntake.command(row['command'])
            evidence = 'gmail-mailbox-proof:' + digest([row['id'], self.email, sender,
                                                       message_id, raw_hash, row['command'], row['receipt']])
            db.execute("UPDATE gmail_reply_challenges SET status='used' WHERE id=?", (row['id'],))
        # A domain rejection or interruption requires owner review/new issuance;
        # a used code is never automatically reapplied to a different message.
        return VerifiedReply(message_id, sender, True, evidence, action, target)
