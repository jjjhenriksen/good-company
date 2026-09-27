"""Verified inbound commands for a trusted provider integration.

A provider must establish identity independently of message display names/body.
No CLI accepts a caller-supplied 'verified' assertion.
"""
from dataclasses import dataclass
import json
from .core import required, stamp, iso, digest
from .providers import ProviderError, authenticated_account


@dataclass(frozen=True)
class VerifiedReply:
    message_id: str
    sender: str
    authenticated: bool
    evidence: str
    action: str
    target_id: str | None = None
    preferences: dict | None = None


def _check_reply_account(coordinator, account):
    # Authentication alone does not put a mailbox inside this organization's
    # remit. Paused sending still permits verified stop/completion responses.
    policy = coordinator.autonomy()
    if (not policy or not isinstance(account.sender, str)
            or account.sender.casefold() != policy['sender'].casefold()):
        raise ProviderError('reply_account_outside_remit')


def apply_verified_reply(coordinator, provider, message_id, now=None):
    account = authenticated_account(provider)
    _check_reply_account(coordinator, account)
    required(message_id, 'provider message ID')
    # This method is supplied by the provider integration, not an arbitrary JSON
    # field or a sender address extracted by the model.
    reply = provider.verified_reply(message_id)
    if not isinstance(reply, VerifiedReply) or not reply.authenticated or reply.message_id != message_id:
        raise ProviderError('unverified_inbound_identity')
    required(reply.evidence, 'provider identity evidence reference')
    required(reply.sender, 'verified sender')
    if reply.action not in ('decline', 'complete', 'stop', 'preferences'):
        raise ProviderError('unsupported_reply_action')
    now = stamp(now)
    db = coordinator.db
    db.execute('''CREATE TABLE IF NOT EXISTS processed_replies(
      id TEXT PRIMARY KEY, status TEXT NOT NULL, at TEXT NOT NULL, evidence TEXT NOT NULL)''')
    reply_id = digest([account.provider, account.account_id, message_id])
    with db:
        db.execute('BEGIN IMMEDIATE')
        # The owner may have changed accounts while the provider read was pending.
        _check_reply_account(coordinator, account)
        if db.execute('SELECT 1 FROM processed_replies WHERE id=?', (reply_id,)).fetchone():
            raise ProviderError('reply_already_processed_or_needs_reconciliation')
        volunteers = [json.loads(row[0]) for row in db.execute('SELECT payload FROM volunteers')]
        actors = [v for v in volunteers if v['email'].casefold() == reply.sender.casefold()]
        if len(actors) != 1:
            raise ProviderError('sender_not_uniquely_mapped_to_verified_roster')
        actor = actors[0]
        authority = 'provider-reply:' + reply_id
        if reply.action in ('decline', 'complete'):
            assignment = db.execute("SELECT * FROM assignments WHERE id=? AND status='assigned'", (reply.target_id,)).fetchone()
            if not assignment or assignment['volunteer_id'] != actor['id']:
                raise ProviderError('reply_target_not_owned_by_sender')
            task = db.execute("SELECT status FROM tasks WHERE id=?", (assignment['task_id'],)).fetchone()
            if not task or task[0] != 'open':
                raise ProviderError('reply_target_not_active')
            if reply.action == 'decline':
                db.execute("UPDATE assignments SET status='declined' WHERE id=?", (reply.target_id,))
                db.execute("UPDATE task_notices SET status='cancelled' WHERE assignment_id=? AND status='pending'", (reply.target_id,))
                coordinator.log('task_declined', reply.target_id, {'authority': authority}, now)
            else:
                db.execute("UPDATE tasks SET status='completed' WHERE id=?", (assignment['task_id'],))
                coordinator._retire_pending(assignment['task_id'])
                coordinator.log('task_completed', assignment['task_id'], {'authority': authority}, now)
        elif reply.action == 'stop':
            address = actor['email'].casefold()
            db.execute('INSERT OR REPLACE INTO contact_consent VALUES(?,?,?,?)', (address, 0, authority, iso(now)))
            for row in db.execute('SELECT id FROM events').fetchall():
                coordinator._invalidate(row['id'])
            for row in db.execute("SELECT id,message FROM task_notices WHERE status='pending'").fetchall():
                message = json.loads(row['message'])
                if address in [a.casefold() for a in message.get('to', []) + message.get('bcc', [])]:
                    db.execute("UPDATE task_notices SET status='cancelled' WHERE id=?", (row['id'],))
            coordinator.log('contact_consent', digest(address)[:24], {'enabled': False, 'authority': authority}, now)
        else:
            # Validate with the same method against isolated state, then write in
            # this transaction so actor checks and mutation cannot race.
            import tempfile
            from pathlib import Path
            from .tasks import WorkCoordinator
            with tempfile.TemporaryDirectory() as directory:
                validator = WorkCoordinator(Path(directory) / 'validation.sqlite')
                try:
                    validator.set_contact_preferences(actor['email'], reply.preferences, authority, now=now)
                finally:
                    validator.db.close()
            db.execute('INSERT OR REPLACE INTO contact_preferences VALUES(?,?)',
                       (actor['email'].casefold(), json.dumps(reply.preferences)))
            for row in db.execute('SELECT id FROM events').fetchall():
                coordinator._invalidate(row['id'])
            coordinator.log('contact_preferences', digest(actor['email'].casefold())[:24], {'authority': authority}, now)
        # Only an opaque identity evidence reference is retained, never raw email.
        db.execute('INSERT INTO processed_replies VALUES(?,?,?,?)', (reply_id, 'applied', iso(now), reply.evidence))
    return {'status': 'applied', 'action': reply.action, 'reference': reply_id}
