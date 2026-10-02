"""The same mailbox proof through an independently authorized Gmail connector.

The trusted host supplies call(tool_name, arguments), invoking the real connector.
No Latch permission is inherited or changed. This transport is explicitly bound
to the connector's authenticated profile before and after every confirmation read.
"""
import sqlite3
from pathlib import Path
import re

from .core import digest
from .google_intake import GoogleReplyProvider
from .providers import Account, ProviderError, SendResult


class GmailConnectorJournal:
    def __init__(self, path, call):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path, timeout=10)
        path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.call = call
        self.db.execute('''CREATE TABLE IF NOT EXISTS connector_sends(
            id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
            outcome TEXT NOT NULL, reference TEXT NOT NULL)''')
        self.db.commit()

    def invoke(self, name, arguments):
        if name not in ('gmail_get_profile', 'gmail_read_email', 'gmail_send_email'):
            raise ProviderError('gmail_connector_tool_outside_scope')
        try:
            result = self.call(name, arguments)
            if (not isinstance(result, dict) or result.get('isError')
                    or not isinstance(result.get('structuredContent'), dict)):
                raise ValueError()
            return result['structuredContent']
        except Exception:
            raise ProviderError('gmail_connector_call_unconfirmed') from None

    def close(self):
        self.db.close()


class GmailConnectorReplies(GoogleReplyProvider):
    """No calendar reads. GmailConnectorJournal is the owner's real host binding."""
    def account(self):
        profile = self.operations.invoke('gmail_get_profile', {})
        if profile.get('email') != self.email or not profile.get('id'):
            raise ProviderError('gmail_connector_account_mismatch')
        return Account('gmail-connector', str(profile['id']), self.email, True,
                       frozenset(), False, bool(self.send_authority and self.unattended),
                       reconcile_send=True)

    def calendar_page(self, *args, **kwargs):
        raise ProviderError('gmail_connector_calendar_unsupported')

    def _message(self, message_id):
        data = self.operations.invoke('gmail_read_email', {'message_id': message_id, 'format': 'raw'})
        # Connector uses snake_case API resource fields; no body reconstruction,
        # synthetic identity verdict or alteration of raw RFC 2822 content.
        return self._confirmation({'id': data.get('id'), 'labelIds': data.get('label_ids'),
                                   'raw': data.get('raw')}, message_id)

    def send(self, message, operation_id, idempotency_key=None):
        if not self.send_authority or idempotency_key is not None:
            raise ProviderError('gmail_connector_send_authority_required')
        batches = self._batches(message)
        if len(batches) != 1 or len(batches[0][0]) != 1 or batches[0][1]:
            raise ProviderError('gmail_connector_single_recipient_required')
        self.account()
        key, fingerprint = self._group(operation_id), digest(message)
        db = self.operations.db
        with db:
            inserted = db.execute('INSERT OR IGNORE INTO connector_sends VALUES(?,?,?,?)',
                                  (key, fingerprint, 'unknown', 'unconfirmed:' + key)).rowcount
        row = db.execute('SELECT * FROM connector_sends WHERE id=?', (key,)).fetchone()
        if row['fingerprint'] != fingerprint:
            raise ProviderError('gmail_connector_send_payload_changed')
        if inserted:
            try:
                result = self.operations.invoke('gmail_send_email', {
                    'to': batches[0][0][0], 'from_address': self.email,
                    'subject': message['subject'],
                    'payload': {'mime_type': 'text/plain', 'charset': 'UTF-8',
                                'body': {'content': message['body']}}})
                uid = result.get('id')
                if not isinstance(uid, str) or not re.fullmatch('[0-9a-fA-F]{1,64}', uid):
                    raise ProviderError('gmail_connector_missing_receipt')
            except ProviderError:
                pass  # Unknown send is never redispatched or activated as proof.
            else:
                with db:
                    db.execute("UPDATE connector_sends SET outcome='accepted',reference=? WHERE id=?",
                               ('gmail:' + uid, key))
        return self.reconcile(operation_id)

    def reconcile(self, operation_id):
        row = self.operations.db.execute('SELECT * FROM connector_sends WHERE id=?',
                                         (self._group(operation_id),)).fetchone()
        if not row:
            raise ProviderError('gmail_connector_unknown_send')
        return SendResult(row['outcome'], row['reference'])
