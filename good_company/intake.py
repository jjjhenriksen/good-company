"""One verified mailbox path for replies, shift signups and cross-workflow replay."""
import re

from .apple_pim import ApplePIMReplies
from .core import digest, iso, stamp
from .providers import ProviderError, authenticated_account
from .replies import VerifiedReply, _check_reply_account, apply_verified_reply
from .signups import apply as apply_signup


class ApplePIMIntake(ApplePIMReplies):
    @staticmethod
    def command(content):
        from .apple_pim import source_text
        text = source_text(content, 'mail').strip()
        match = re.fullmatch(r'(SIGNUP|ACCEPT|DECLINE-OFFER) ([A-Za-z0-9_.:/-]{1,200})', text, re.IGNORECASE)
        if match:
            return {'SIGNUP': 'signup', 'ACCEPT': 'accept_offer', 'DECLINE-OFFER': 'decline_offer'}[match[1].upper()], match[2]
        return ApplePIMReplies.command(content)


class _BoundReply:
    def __init__(self, account, reply):
        self.identity, self.reply = account, reply

    def account(self):
        return self.identity

    def verified_reply(self, message_id):
        if message_id != self.reply.message_id:
            raise ProviderError('intake_message_id_changed')
        return self.reply


def dispatch(coordinator, provider, message_id, now=None):
    before = authenticated_account(provider)
    _check_reply_account(coordinator, before)
    reply = provider.verified_reply(message_id)
    after = authenticated_account(provider)
    if before != after:
        raise ProviderError('intake_account_changed_during_read')
    if not isinstance(reply, VerifiedReply) or reply.message_id != message_id or reply.authenticated is not True or not reply.evidence:
        raise ProviderError('intake_unverified_identity')
    if reply.action in ('signup', 'accept_offer', 'decline_offer'):
        apply = apply_signup
    elif reply.action in ('decline', 'complete', 'stop', 'preferences'):
        apply = apply_verified_reply
    else:
        raise ProviderError('intake_unsupported_action')
    now = stamp(now)
    key = digest([before.provider, before.account_id, message_id])
    db = coordinator.db
    db.execute('''CREATE TABLE IF NOT EXISTS inbound_intake(
        id TEXT PRIMARY KEY, status TEXT NOT NULL, action TEXT NOT NULL,
        evidence TEXT NOT NULL, at TEXT NOT NULL)''')
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM inbound_intake WHERE id=?', (key,)).fetchone():
            raise ProviderError('intake_already_claimed_or_needs_review')
        db.execute('INSERT INTO inbound_intake VALUES(?,?,?,?,?)', (key, 'claimed', reply.action, reply.evidence, iso(now)))
    try:
        result = apply(coordinator, _BoundReply(before, reply), message_id, now=now)
    except Exception as error:
        # Domain handlers roll back rejected mutations. Unexpected failures may
        # occur after a commit; no automatic replay or invented success follows.
        with db:
            db.execute('UPDATE inbound_intake SET status=? WHERE id=?',
                       ('rejected' if isinstance(error, ProviderError) else 'uncertain', key))
        raise
    with db:
        db.execute("UPDATE inbound_intake SET status='applied' WHERE id=?", (key,))
    return {**result, 'intake_reference': key}
