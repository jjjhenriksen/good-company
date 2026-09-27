"""Explicit, audited corrections. Provider sends remain outside the local ledger."""
import json
from datetime import timedelta
from zoneinfo import ZoneInfo
from .core import required, digest, stamp, iso
from .tasks import WorkCoordinator


class CorrectionCoordinator(WorkCoordinator):
    def __init__(self, path):
        super().__init__(path)


    def _correction_context(self, kind, original_id):
        policy = self.autonomy()
        if not policy or not policy['enabled']:
            raise ValueError('Corrections require an active standing communication remit.')
        if kind == 'event':
            original = self.db.execute('SELECT * FROM reminders WHERE id=?', (original_id,)).fetchone()
            if not original or not original['claimed_at']:
                raise ValueError('Correct only a previously attempted notice.')
            event = self.db.execute('SELECT * FROM events WHERE id=?', (original['event_id'],)).fetchone()
            payload = json.loads(event['payload'])
            if event['calendar'] not in policy['calendar_scopes'] or payload.get('event_type') not in policy['allowed_event_types']:
                raise ValueError('Event correction is outside the current remit.')
            revision = digest([event['revision'], event['cancelled']])
        elif kind == 'task':
            original = self.db.execute('SELECT * FROM task_notices WHERE id=?', (original_id,)).fetchone()
            if not original:
                raise ValueError('Unknown original notice.')
            assignment = self.db.execute('SELECT * FROM assignments WHERE id=?', (original['assignment_id'],)).fetchone()
            task = self.db.execute('SELECT * FROM tasks WHERE id=?', (assignment['task_id'],)).fetchone()
            payload = json.loads(task['payload'])
            if payload['category'] not in policy['allowed_task_categories']:
                raise ValueError('Task correction is outside the current remit.')
            revision = digest([dict(task), dict(assignment)])
        else:
            raise ValueError('Correction kind must be event or task.')
        if original['status'] not in ('sent', 'failed'):
            raise ValueError('Reconcile the original provider attempt before creating a correction.')
        return original, revision, policy

    def _validate_correction(self, message, original, policy):
        if not isinstance(message, dict) or set(message) != {'sender', 'to', 'bcc', 'subject', 'body'}:
            raise ValueError('Correction needs exactly sender, to, bcc, subject and body.')
        required(message['subject'], 'correction subject')
        required(message['body'], 'correction body')
        if any(not isinstance(message[key], list) or any(not isinstance(a, str) for a in message[key]) for key in ('to', 'bcc')):
            raise ValueError('Recipient fields must be address lists.')
        recipients = message['to'] + message['bcc']
        previous = json.loads(original['message'])
        allowed = set(previous.get('to', []) + previous.get('bcc', [])) & set(policy['allowed_recipients'])
        if not recipients or len(recipients) != len(set(recipients)) or not set(recipients) <= allowed:
            raise ValueError('Corrections may contact only still-authorized original recipients.')
        if message['sender'] != policy['sender']:
            raise ValueError('Use the current authorized sender.')
        if any(not self.contact_allowed(a) for a in recipients):
            raise ValueError('A correction recipient has withdrawn consent.')

    def create_correction(self, kind, original_id, message, expected_hash, authority, now=None):
        required(authority, 'verified correction authority and source reference')
        if digest(message) != expected_hash:
            raise ValueError('Correction content differs from the reviewed message.')
        now = stamp(now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            original, revision, policy = self._correction_context(kind, original_id)
            self._validate_correction(message, original, policy)
            cid = digest([kind, original_id, revision])[:24]
            previous = self.db.execute('SELECT message FROM corrections WHERE id=?', (cid,)).fetchone()
            if previous and json.loads(previous[0]) != message:
                raise ValueError('This revision already has a correction; reconcile it rather than issuing a duplicate.')
            self.db.execute("INSERT OR IGNORE INTO corrections VALUES(?,?,?,?,?,?,'pending',?,NULL,?)",
                            (cid, kind, original_id, revision, digest(policy), json.dumps(message), iso(now), authority))
            self.log('correction_authorized', cid, {'original_id': original_id, 'authority': authority}, now)
        return {'id': cid, 'original_id': original_id, 'original_provider_state': original['status']}

    def correction_queue(self):
        return [dict(r) | {'message': json.loads(r['message'])} for r in self.db.execute('SELECT * FROM corrections ORDER BY created_at,id')]

    def correction_claim(self, correction_id, now=None):
        now = stamp(now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM corrections WHERE id=?', (correction_id,)).fetchone()
            if not row or row['status'] != 'pending':
                raise ValueError('Correction is not pending; never resend an attempted correction.')
            original, revision, policy = self._correction_context(row['kind'], row['original_id'])
            if revision != row['revision'] or digest(policy) != row['policy_hash']:
                raise ValueError('Correction context changed; reconcile current source and authority.')
            if not stamp(row['created_at']) <= now < stamp(row['created_at']) + timedelta(hours=24):
                raise ValueError('Correction authorization has expired.')
            if row['kind'] == 'event':
                checked = self.db.execute('SELECT checked_at FROM events WHERE id=?', (original['event_id'],)).fetchone()[0]
                if not timedelta(0) <= now - stamp(checked) <= timedelta(minutes=15):
                    raise ValueError('Refresh the calendar before sending a correction.')
            message = json.loads(row['message'])
            self._validate_correction(message, original, policy)
            if not 7 <= now.astimezone(ZoneInfo(self.profile()['timezone'])).hour < 21:
                raise ValueError('Quiet hours; correction remains queued.')
            self._check_communication_budget(now)
            self._check_contacts(message, now)
            self._record_contacts('correction', correction_id, message, now)
            self.db.execute("UPDATE corrections SET status='sending' WHERE id=?", (correction_id,))
            self.log('correction_claim', correction_id, {}, now)
        return {'id': correction_id, 'message': message, 'instruction': 'Send this exact content to these recipients once. BCC-only groups may use private individual copies without adding recipients. Record every provider receipt. Unknown outcomes require reconciliation.'}

    def correction_receipt(self, correction_id, outcome, provider_id, now=None):
        if outcome not in ('sent', 'failed', 'uncertain'):
            raise ValueError('Unknown correction outcome.')
        required(provider_id, 'provider receipt or error reference')
        with self.db:
            changed = self.db.execute("UPDATE corrections SET status=?,receipt=? WHERE id=? AND status IN ('sending','uncertain')",
                                      (outcome, provider_id, correction_id)).rowcount
            if changed != 1:
                raise ValueError('No outstanding correction attempt to reconcile.')
            self.log('correction_' + outcome, correction_id, {'receipt': provider_id}, stamp(now))
        return {'id': correction_id, 'status': outcome}
