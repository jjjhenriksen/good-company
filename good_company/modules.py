"""Optional workflows in the trusted owner's workspace.

Actor/evidence references are host attestations, never authentication. Verify an
incoming identity before invoking these owner tools. No volunteer permission is
inherited and a local record never establishes external fulfillment.
"""
import json
import re
from datetime import timedelta
from zoneinfo import ZoneInfo
from .core import digest, iso, required, required_time, stamp
from .onboarding import SetupCoordinator

MODULES = ('resources', 'accessibility', 'checklists', 'relationships')
POLICY_FIELDS = {'enabled', 'owners', 'people', 'source', 'retention_days', 'notice_recipients'}


def text(value, label, limit=200):
    value = required(value, label)
    if len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(label + ' must be bounded single-line text.')
    return value


def fields(value, allowed, mandatory=()):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(mandatory) - set(value):
        raise ValueError('Supply only the documented fields, including required fields.')
    return dict(value)


class ModuleCoordinator(SetupCoordinator):
    def __init__(self, path):
        super().__init__(path)
        with self.db:
            self.db.execute('''CREATE TABLE IF NOT EXISTS module_policies(
                module TEXT PRIMARY KEY, payload TEXT NOT NULL)''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS module_records(
                module TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
                payload TEXT NOT NULL, status TEXT NOT NULL, expires_at TEXT NOT NULL,
                PRIMARY KEY(module,id))''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS module_notices(
                id TEXT PRIMARY KEY, module TEXT NOT NULL, record_id TEXT NOT NULL,
                revision INTEGER NOT NULL, policy_hash TEXT NOT NULL,
                due TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL,
                receipt TEXT)''')

    def configure_module(self, module, policy, authority, now=None):
        text(authority, 'owner instruction reference')
        if module not in MODULES:
            raise ValueError('Unknown optional workflow.')
        p = fields(policy, POLICY_FIELDS, POLICY_FIELDS)
        if type(p['enabled']) is not bool:
            raise ValueError('enabled must be true or false.')
        if type(p['retention_days']) is not int or not 1 <= p['retention_days'] <= 365:
            raise ValueError('Choose retention from 1 to 365 days.')
        p['source'] = text(p['source'], 'authoritative source')
        if module == 'resources' and p['source'] != 'good-company-ledger':
            raise ValueError('Resource booking supports the Good Company reservation ledger only.')
        if not isinstance(p['people'], dict) or not p['people'] or len(p['people']) > 1000:
            raise ValueError('Supply the workflow-specific verified people.')
        p['people'] = {key: dict(value) if isinstance(value, dict) else value for key, value in p['people'].items()}
        for principal, person in p['people'].items():
            text(principal, 'verified principal')
            fields(person, {'email'})
            if person.get('email') is not None:
                if not isinstance(person['email'], str) or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', person['email']):
                    raise ValueError('Use verified single email addresses.')
                person['email'] = person['email'].casefold()
        emails = [v['email'] for v in p['people'].values() if v.get('email')]
        if len(set(emails)) != len(emails):
            raise ValueError('Each workflow mailbox must belong to one principal.')
        if (not isinstance(p['owners'], list) or not p['owners']
                or any(not isinstance(v, str) or v not in p['people'] for v in p['owners'])
                or len(set(p['owners'])) != len(p['owners'])):
            raise ValueError('Name distinct owners from the verified workflow people.')
        recipients = p['notice_recipients']
        if (not isinstance(recipients, list) or any(not isinstance(a, str) for a in recipients)
                or len({a.casefold() for a in recipients}) != len(recipients)
                or any(a.casefold() not in emails for a in recipients)):
            raise ValueError('Notice recipients must be distinct verified workflow mailboxes.')
        p['notice_recipients'] = [a.casefold() for a in recipients]
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload FROM module_policies WHERE module=?', (module,)).fetchone()
            if not old or json.loads(old[0]) != p:
                self.db.execute('INSERT OR REPLACE INTO module_policies VALUES(?,?)', (module, json.dumps(p)))
                self.db.execute("UPDATE module_notices SET status='superseded' WHERE module=? AND status='pending'", (module,))
                self.log('module_configured', module, {'authority_hash': digest(authority), 'policy_hash': digest(p)}, stamp(now))
        return {'module': module, 'enabled': p['enabled']}

    def _module_policy(self, module, actor=None):
        row = self.db.execute('SELECT payload FROM module_policies WHERE module=?', (module,)).fetchone()
        if not row or not json.loads(row[0])['enabled']:
            raise ValueError('This optional workflow is unconfigured or paused.')
        policy = json.loads(row[0])
        if actor is not None and actor not in policy['people']:
            raise ValueError('The verified person is outside this workflow.')
        return policy

    def _module_owner(self, module, actor):
        policy = self._module_policy(module, actor)
        if actor not in policy['owners']:
            raise ValueError('This operation requires a named workflow owner.')
        return policy

    def _expiry(self, policy, now):
        return iso(stamp(now) + timedelta(days=policy['retention_days']))

    def _record(self, module, record_id, actor=None, now=None):
        policy = self._module_policy(module, actor)
        row = self.db.execute('SELECT * FROM module_records WHERE module=? AND id=?', (module, record_id)).fetchone()
        if not row or stamp(row['expires_at']) <= stamp(now) or row['status'] == 'expired':
            raise ValueError('No current record is available.')
        record = json.loads(row['payload'])
        if record.get('source') != policy['source']:
            raise ValueError('The authoritative workflow source changed; reconcile the record.')
        if actor is not None and actor not in record['viewers']:
            raise ValueError('This record is outside the verified person\'s access.')
        return dict(row) | {'payload': record}

    def _event_binding(self, event_id):
        if not event_id:
            return {}
        event = self.db.execute('SELECT calendar,revision,cancelled FROM events WHERE id=?', (event_id,)).fetchone()
        policy = self.autonomy()
        if not event or event['cancelled'] or not policy or event['calendar'] not in policy['calendar_scopes']:
            raise ValueError('Use a current event in the authorized calendar scope.')
        return {'event_id': event_id, 'event_revision': event['revision']}

    def _event_valid(self, record):
        if not record.get('event_id'):
            return True
        try:
            return self._event_binding(record['event_id'])['event_revision'] == record['event_revision']
        except ValueError:
            return False

    def _save_record(self, module, record_id, payload, status, expires_at, authority, now, revision=1):
        text(record_id, 'record ID')
        text(authority, 'verified operation reference')
        self.db.execute('''INSERT INTO module_records VALUES(?,?,?,?,?,?)
            ON CONFLICT(module,id) DO UPDATE SET revision=excluded.revision,
            payload=excluded.payload,status=excluded.status,expires_at=excluded.expires_at''',
            (module, record_id, revision, json.dumps(payload), status, expires_at))
        self.db.execute("UPDATE module_notices SET status='superseded' WHERE module=? AND record_id=? AND revision<>? AND status='pending'",
                        (module, record_id, revision))
        self.log('module_record_changed', digest([module, record_id]),
                 {'module': module, 'status': status, 'revision': revision, 'authority_hash': digest(authority)}, stamp(now))
        return {'id': record_id, 'status': status, 'revision': revision}

    def module_status(self, module, record_id, actor, now=None):
        row = self._record(module, record_id, actor, now)
        return {'id': record_id, 'status': row['status'] if self._event_valid(row['payload']) else 'needs_review',
                'revision': row['revision'], 'expires_at': row['expires_at'], 'record': row['payload']}

    def module_summary(self):
        return {'counts': [dict(r) for r in self.db.execute('''SELECT module,status,count(*) AS count
                FROM module_records GROUP BY module,status ORDER BY module,status''')],
                'scope': 'Aggregate local status; no identities, request text or external fulfillment claims.'}

    def expire_module_records(self, authority, now=None):
        text(authority, 'owner retention reference')
        now = stamp(now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            rows = self.db.execute("SELECT module,id FROM module_records WHERE expires_at<=? AND status<>'expired'", (iso(now),)).fetchall()
            for row in rows:
                self.db.execute("UPDATE module_records SET payload='{}',status='expired',revision=revision+1 WHERE module=? AND id=?", tuple(row))
                self.db.execute("UPDATE module_notices SET status=CASE WHEN status='pending' THEN 'superseded' ELSE status END,message=? WHERE module=? AND record_id=? AND status NOT IN ('sending','uncertain')",
                                (json.dumps({'subject': '[expired]', 'body': '[expired]'}), *tuple(row)))
            if rows:
                self.log('module_retention', 'optional-workflows', {'count': len(rows), 'authority_hash': digest(authority)}, now)
        return {'expired': len(rows), 'scope': 'Logical deletion. Unknown delivery evidence and ID tombstones remain; backups are not erased.'}

    def module_notice(self, module, record_id, recipient, due, actor, authority, now=None):
        text(authority, 'notice authority')
        now, due = stamp(now), required_time(due, 'notice due time')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            record = self._record(module, record_id, actor, now)
            p = self._module_policy(module, actor)
            if actor not in p['owners'] and actor != record['payload'].get('subject'):
                raise ValueError('Only the subject or workflow owner can queue a notice.')
            self._notice_recipient(p, record, recipient)
            if not now <= due < stamp(record['expires_at']) or not self._event_valid(record['payload']):
                raise ValueError('Notice timing or event evidence is no longer current.')
            self._notice_current(module, record, now)
            message = {'sender': (self.autonomy() or {}).get('sender'), 'to': [recipient.casefold()], 'bcc': [],
                       'subject': 'Good Company: ' + module + ' update',
                       'body': 'Your ' + module + ' record has status: ' + record['status'] + '.\nAsk your coordinator for the current details.'}
            policy_hash = digest([p, self.autonomy()])
            for previous in self.db.execute('SELECT id,status,message FROM module_notices WHERE module=? AND record_id=? AND revision=?', (module, record_id, record['revision'])):
                if previous['status'] in ('sending', 'uncertain', 'sent', 'failed') and json.loads(previous['message']).get('to') == message['to']:
                    return {'id': previous['id'], 'status': previous['status']}
            nid = digest([module, record_id, record['revision'], policy_hash, recipient.casefold()])[:32]
            self.db.execute("INSERT OR IGNORE INTO module_notices VALUES(?,?,?,?,?,?,'pending',?,NULL)",
                            (nid, module, record_id, record['revision'], policy_hash, iso(due), json.dumps(message)))
        return {'id': nid, 'status': self.db.execute('SELECT status FROM module_notices WHERE id=?', (nid,)).fetchone()[0]}

    def _notice_recipient(self, policy, record, recipient):
        if not isinstance(recipient, str):
            raise ValueError('Use a verified recipient.')
        address = recipient.casefold()
        viewers = [policy['people'][v].get('email') for v in record['payload']['viewers'] if v in policy['people']]
        if address not in viewers or address not in policy['notice_recipients']:
            raise ValueError('This recipient has no workflow-specific notice authority.')

    def _notice_current(self, module, record, now):
        if record['status'] in ('withdrawn', 'cancelled', 'expired'):
            raise ValueError('This record no longer authorizes notices.')

    def module_queue(self):
        return [dict(r) | {'message': json.loads(r['message'])} for r in self.db.execute('SELECT * FROM module_notices ORDER BY due,id')]

    def module_claim(self, notice_id, now=None):
        now = stamp(now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM module_notices WHERE id=?', (notice_id,)).fetchone()
            if not row or row['status'] != 'pending' or stamp(row['due']) > now:
                raise ValueError('This notice is not due or has already been attempted.')
            p = self._module_policy(row['module'])
            record = self._record(row['module'], row['record_id'], now=now)
            policy = self.autonomy()
            if not policy or not policy['enabled'] or row['policy_hash'] != digest([p, policy]):
                raise ValueError('The standing notice authority changed or is paused.')
            if record['revision'] != row['revision'] or not self._event_valid(record['payload']):
                raise ValueError('The record or event changed; prepare a current notice.')
            self._notice_current(row['module'], record, now)
            message = json.loads(row['message'])
            self._notice_recipient(p, record, message['to'][0])
            if message['sender'] != policy['sender'] or message['to'][0] not in [a.casefold() for a in policy['allowed_recipients']]:
                raise ValueError('The sender or recipient is outside the standing remit.')
            if not 8 <= now.astimezone(ZoneInfo(self.profile()['timezone'])).hour < 21:
                raise ValueError('Deferred: organization quiet hours; leave the notice queued.')
            self._check_contacts(message, now)
            self._check_communication_budget(now)
            self.db.execute("UPDATE module_notices SET status='sending' WHERE id=?", (notice_id,))
            self._record_contacts('module', notice_id, message, now)
            self.log('module_notice_claim', notice_id, {}, now)
        return {'id': notice_id, 'message': message}

    def module_receipt(self, notice_id, outcome, provider_id, now=None):
        text(provider_id, 'actual provider receipt or uncertainty reference', 500)
        if outcome not in ('sent', 'failed', 'uncertain'):
            raise ValueError('Record a truthful provider outcome.')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT status,receipt FROM module_notices WHERE id=?', (notice_id,)).fetchone()
            if not row:
                raise ValueError('Unknown notice.')
            if row['status'] == outcome and row['receipt'] == provider_id:
                return {'id': notice_id, 'status': outcome}
            if row['status'] not in ('sending', 'uncertain'):
                raise ValueError('Only an attempted or unknown notice can receive an outcome.')
            self.db.execute('UPDATE module_notices SET status=?,receipt=? WHERE id=?', (outcome, provider_id, notice_id))
        return {'id': notice_id, 'status': outcome}

    def add_resource(self, *args, **request):
        from .resources import add_resource
        return add_resource(self, *args, **request)

    def book_resource(self, *args, **request):
        from .resources import book_resource
        return book_resource(self, *args, **request)

    def cancel_booking(self, *args, **request):
        from .resources import cancel_booking
        return cancel_booking(self, *args, **request)

    def resource_availability(self, *args, **request):
        from .resources import resource_availability
        return resource_availability(self, *args, **request)

    def request_accessibility(self, *args, **request):
        from .access_requests import request_accessibility
        return request_accessibility(self, *args, **request)

    def update_accessibility(self, *args, **request):
        from .access_requests import update_accessibility
        return update_accessibility(self, *args, **request)
