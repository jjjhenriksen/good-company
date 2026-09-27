"""Autonomous allocation and communication queue for an authorized volunteer team.

Provider calls remain in the OpenClaw skill. This engine never fabricates sends.
"""
import json
import re
from datetime import timedelta
from zoneinfo import ZoneInfo
from .core import Coordinator, required, stamp, iso, digest


class WorkCoordinator(Coordinator):
    def __init__(self, path):
        super().__init__(path)


    def set_volunteer(self, volunteer, authority, now=None):
        required(authority, 'roster source or authorization reference')
        v = dict(volunteer)
        for key in ('id', 'name', 'email'):
            required(v.get(key), key)
        if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', v['email']):
            raise ValueError('Use the verified volunteer email address.')
        if type(v.get('accepts_delegation')) is not bool:
            raise ValueError('Record whether the volunteer accepts routine delegation.')
        if type(v.get('max_open_tasks')) is not int or not 1 <= v['max_open_tasks'] <= 20:
            raise ValueError('max_open_tasks must be 1–20.')
        if not isinstance(v.get('skills'), dict) or any(type(n) is not int or not 0 <= n <= 3 for n in v['skills'].values()):
            raise ValueError('skills must map stated skill names to proficiency 0–3.')
        for key in ('roles', 'avoid_categories', 'preferred_categories', 'availability'):
            if not isinstance(v.get(key), list):
                raise ValueError(f'{key} must be a list.')
        for interval in v['availability']:
            if stamp(interval['start']) >= stamp(interval['end']):
                raise ValueError('Availability end must follow start.')
        credentials = v.get('credentials', [])
        if not isinstance(credentials, list):
            raise ValueError('credentials must be a list of verified evidence records.')
        for credential in credentials:
            if not isinstance(credential, dict):
                raise ValueError('Each credential must be an object.')
            for key in ('name', 'evidence', 'issuer'):
                required(credential.get(key), 'credential ' + key)
            if not stamp(credential['valid_from']) < stamp(credential['valid_until']):
                raise ValueError('Credential validity must have a positive interval.')
            if not isinstance(credential.get('categories'), list) or not credential['categories'] or any(not isinstance(c, str) or not c.strip() or c == '*' for c in credential['categories']):
                raise ValueError('Credential categories must be explicit task categories.')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO volunteers VALUES(?,?)', (v['id'], json.dumps(v)))
            self.log('volunteer_update', v['id'], {'authority': authority}, stamp(now))
        return {'volunteer_id': v['id']}

    def add_task(self, task, authority, now=None):
        required(authority, 'todo-list authority reference')
        t = dict(task)
        for key in ('id', 'title', 'category'):
            required(t.get(key), key)
        if not stamp(t['start']) < stamp(t['end']):
            raise ValueError('Task end must follow start.')
        if not isinstance(t.get('eligible_roles'), list) or not t['eligible_roles']:
            raise ValueError('Supply the roles eligible for this task.')
        if t.get('role_match', 'ANY') not in ('ANY', 'ALL'):
            raise ValueError('role_match must be ANY or ALL.')
        if any(not isinstance(role, str) or not role.strip() for role in t['eligible_roles']):
            raise ValueError('Eligible roles must be explicit nonempty names.')
        if not isinstance(t.get('required_skills'), dict) or any(type(n) is not int or not 1 <= n <= 3 for n in t['required_skills'].values()):
            raise ValueError('required_skills must map skills to minimum proficiency 1–3.')
        if not isinstance(t.get('preferred_skills'), list):
            raise ValueError('preferred_skills must be a list.')
        if t.get('event_id'):
            event = self.db.execute('SELECT revision,payload,cancelled FROM events WHERE id=?', (t['event_id'],)).fetchone()
            if not event or event['cancelled']:
                raise ValueError('Link tasks only to an existing active event.')
            t['event_revision'] = event['revision']
            t['event_start'] = json.loads(event['payload'])['start']
        credentials = t.get('required_credentials', [])
        if not isinstance(credentials, list) or any(not isinstance(c, str) or not c.strip() for c in credentials):
            raise ValueError('required_credentials must be a list of named qualifications.')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT payload FROM tasks WHERE id=?', (t['id'],)).fetchone()
            if old and json.loads(old[0]) != t:
                raise ValueError('Existing tasks are immutable: complete/cancel and explicitly replace changed assignments.')
            self.db.execute("INSERT OR IGNORE INTO tasks VALUES(?,?,'open')", (t['id'], json.dumps(t)))
            self.log('task_added', t['id'], {'authority': authority}, stamp(now))
        return {'task_id': t['id']}

    def _workload(self, volunteer_id, excluding=None):
        return [json.loads(r[0]) for r in self.db.execute('''SELECT t.payload FROM tasks t
          JOIN assignments a ON a.task_id=t.id WHERE a.volunteer_id=? AND a.status IN ('assigned','offered')
          AND t.status='open' AND t.id<>?''', (volunteer_id, excluding or ''))]

    def _event_current(self, task):
        if not task.get('event_id'):
            return True
        row = self.db.execute('SELECT revision,cancelled FROM events WHERE id=?', (task['event_id'],)).fetchone()
        return bool(row and not row['cancelled'] and row['revision'] == task.get('event_revision'))

    def task_impacts(self):
        impacts = []
        for row in self.db.execute("SELECT id,payload FROM tasks WHERE status='open'"):
            task = json.loads(row['payload'])
            if self._event_current(task):
                continue
            event = self.db.execute('SELECT revision,start,cancelled FROM events WHERE id=?', (task['event_id'],)).fetchone()
            cancelled = not event or bool(event['cancelled'])
            proposed = None
            if not cancelled:
                shift = stamp(event['start']) - stamp(task['event_start'])
                proposed = {'start': iso(stamp(task['start']) + shift), 'end': iso(stamp(task['end']) + shift)}
            attempts = self.db.execute("""SELECT n.id,n.status,n.receipt FROM task_notices n
              JOIN assignments a ON a.id=n.assignment_id WHERE a.task_id=?
              AND n.status IN ('sending','sent','uncertain','failed')""", (row['id'],)).fetchall()
            impacts.append({'task_id': row['id'], 'event_id': task['event_id'],
                            'reason': 'event_cancelled' if cancelled else 'event_changed',
                            'proposed_window': proposed, 'attempts': [dict(a) for a in attempts],
                            'next': 'Cancel the old task; for a changed event, verify availability and explicitly add a replacement with a new ID. Reconcile attempted notices separately.'})
        return {'impacts': impacts}

    def import_calendar(self, snapshot, now=None):
        result = super().import_calendar(snapshot, now=now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            for row in self.db.execute("SELECT id,payload FROM tasks WHERE status='open'").fetchall():
                if not self._event_current(json.loads(row['payload'])):
                    self._retire_pending(row['id'])
        return result | self.task_impacts()

    def _credential_gaps(self, v, t):
        return [name for name in t.get('required_credentials', [])
                if not any(c['name'] == name and t['category'] in c['categories']
                           and stamp(c['valid_from']) <= stamp(t['start'])
                           and stamp(c['valid_until']) >= stamp(t['end'])
                           for c in v.get('credentials', []))]

    def _eligible(self, v, t, policy):
        workload = self._workload(v['id'], t['id'])
        if not self._event_current(t):
            return False
        if not self.contact_allowed(v['email']) or self._credential_gaps(v, t):
            return False
        if not v['accepts_delegation'] or v['email'] not in policy['allowed_recipients']:
            return False
        roles, required_roles = set(v['roles']), set(t['eligible_roles'])
        matches = required_roles <= roles if t.get('role_match', 'ANY') == 'ALL' else bool(required_roles & roles)
        if t['category'] in v['avoid_categories'] or not matches:
            return False
        if any(v['skills'].get(skill, 0) < level for skill, level in t['required_skills'].items()):
            return False
        if len(workload) >= v['max_open_tasks']:
            return False
        if not any(stamp(w['start']) <= stamp(t['start']) and stamp(w['end']) >= stamp(t['end']) for w in v['availability']):
            return False
        return not any(stamp(w['start']) < stamp(t['end']) and stamp(w['end']) > stamp(t['start']) for w in workload)

    def _notice(self, assignment_id, t, v, kind, due, policy):
        aid = digest([assignment_id, kind])[:24]
        from .localization import date_text, time_text, term
        profile = self.profile()
        date = date_text(t['start'], profile) + ' at ' + time_text(t['start'], profile)
        task_term = term(profile, 'task')
        prefix = 'Your ' + task_term if kind == 'assignment' else task_term.capitalize() + ' reminder'
        message = {'sender': policy['sender'], 'to': [v['email']], 'bcc': [],
                   'subject': f'{prefix}: {t["title"]}',
                   'body': f'Hi {v["name"]},\n\n{t["title"]}\nWhen: {date}\n\nThis is within the work you agreed to help with. If your availability has changed, reply and I will find another arrangement.\n\n{self.profile()["signoff"]}'}
        self.db.execute("""INSERT INTO task_notices VALUES(?,?,?,?,'pending',?,NULL)
          ON CONFLICT(id) DO UPDATE SET message=excluded.message,status='pending'
          WHERE task_notices.status IN ('pending','cancelled')""",
                        (aid, assignment_id, kind, iso(due), json.dumps(message)))

    def _retire_pending(self, task_id):
        self.db.execute("""UPDATE task_notices SET status='cancelled' WHERE status='pending'
          AND assignment_id IN (SELECT id FROM assignments WHERE task_id=?)""", (task_id,))

    def delegate(self, now=None):
        now = stamp(now)
        made, exceptions = [], []
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            policy = self.autonomy()
            if not policy or not policy['enabled']:
                return {'assigned': [], 'exceptions': [{'reason': 'Configure standing delegation instructions first.'}]}
            allowed_kinds = {'assignment'} | {f'{h}h' for h in policy.get('task_reminder_hours', [24])}
            for notice in self.db.execute("SELECT id,kind FROM task_notices WHERE status='pending'").fetchall():
                if notice['kind'] not in allowed_kinds:
                    self.db.execute("UPDATE task_notices SET status='cancelled' WHERE id=?", (notice['id'],))
                    self.log('task_notice_cadence_revoked', notice['id'], {}, now)
            volunteers = [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM volunteers ORDER BY id')]
            tasks = sorted([json.loads(r[0]) for r in self.db.execute("SELECT payload FROM tasks WHERE status='open'")], key=lambda t: (stamp(t['start']), t['id']))
            for t in tasks:
                if not self._event_current(t):
                    self._retire_pending(t['id'])
                    exceptions.append({'task_id': t['id'], 'reason': 'Linked event changed; review task_impacts and verified availability.'})
                    continue
                if stamp(t['start']) <= now:
                    self._retire_pending(t['id'])
                    continue
                if t['category'] not in policy['allowed_task_categories']:
                    self._retire_pending(t['id'])
                    exceptions.append({'task_id': t['id'], 'reason': 'Task category is outside standing instructions.'})
                    continue
                existing = self.db.execute("SELECT * FROM assignments WHERE task_id=? AND status='assigned'", (t['id'],)).fetchone()
                if not existing and t.get('signup_required'):
                    # A decline while paused may leave an eligible waitlist behind.
                    # Resume only its opt-in offers, never automatic assignment.
                    from .signups import promote_waitlist
                    promote_waitlist(self, t['id'], now)
                    continue
                if existing:
                    v = next((v for v in volunteers if v['id'] == existing['volunteer_id']), None)
                    if not v or not self._eligible(v, t, policy):
                        self._retire_pending(t['id'])
                        exceptions.append({'task_id': t['id'], 'reason': 'An existing assignment needs reconciliation after availability or role changed.'})
                        continue
                    assignment_id = existing['id']
                    self.db.execute('UPDATE assignments SET policy_hash=? WHERE id=?', (digest(policy), assignment_id))
                    self._notice(assignment_id, t, v, 'assignment', now, policy)
                    # Include overdue notices that fall outside the cadence creation
                    # window. Only never-attempted rows may get new routing.
                    for pending in self.db.execute("SELECT kind,due FROM task_notices WHERE assignment_id=? AND status='pending'", (assignment_id,)).fetchall():
                        if pending['kind'] in allowed_kinds:
                            self._notice(assignment_id, t, v, pending['kind'], pending['due'], policy)
                else:
                    declined = {r[0] for r in self.db.execute("SELECT volunteer_id FROM assignments WHERE task_id=? AND status='declined'", (t['id'],))}
                    candidates = [v for v in volunteers if v['id'] not in declined and self._eligible(v, t, policy)]
                    if not candidates:
                        exceptions.append({'task_id': t['id'], 'reason': ('Required credential evidence is missing, expired or inapplicable.' if t.get('required_credentials') and all(self._credential_gaps(v, t) for v in volunteers) else 'No eligible, available volunteer has capacity.')})
                        continue
                    def rank(v):
                        matches = sum(v['skills'].get(s, 0) for s in t['preferred_skills'])
                        preference = int(t['category'] in v['preferred_categories'])
                        return (-matches, -preference, len(self._workload(v['id'])), v['id'])
                    v = sorted(candidates, key=rank)[0]
                    selection = {'eligible_candidates': len(candidates),
                                 'preferred_fit_points': sum(v['skills'].get(skill, 0) for skill in t['preferred_skills']),
                                 'preferred_category': t['category'] in v['preferred_categories'],
                                 'open_work_before': len(self._workload(v['id'])),
                                 'order': 'Eligible first; preferred task fit, recorded category preference, lower open workload, then stable ID.'}
                    assignment_id = digest([t['id'], v['id']])[:24]
                    self.db.execute("INSERT INTO assignments VALUES(?,?,?,'assigned',?)", (assignment_id, t['id'], v['id'], digest(policy)))
                    self._notice(assignment_id, t, v, 'assignment', now, policy)
                    self.log('task_delegated', t['id'], {'assignment_id': assignment_id, 'volunteer_id': v['id'], 'selection': selection}, now)
                    made.append({'task_id': t['id'], 'volunteer_id': v['id'], 'assignment_id': assignment_id,
                                 'reason': 'Matches the stated skills, role, availability and workload limits.',
                                 'delivery': 'queued, not yet sent'})
                for hours in policy.get('task_reminder_hours', [24]):
                    if type(hours) is not int or not 1 <= hours <= 168:
                        raise ValueError('Task reminder cadence must use 1–168 whole hours.')
                    due = stamp(t['start']) - timedelta(hours=hours)
                    if due > now or (existing and due >= now - timedelta(minutes=15)):
                        self._notice(assignment_id, t, v, f'{hours}h', due, policy)
        return {'assigned': made, 'exceptions': exceptions}

    def task_queue(self):
        return [dict(r) | {'message': json.loads(r['message'])} for r in
                self.db.execute('SELECT * FROM task_notices ORDER BY due,id')]

    def task_claim(self, notice_id, now=None):
        now = stamp(now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            policy = self.autonomy()
            if not policy or not policy['enabled']:
                raise ValueError('Autonomy is paused or unconfigured.')
            if not 7 <= now.astimezone(ZoneInfo(self.profile()['timezone'])).hour < 21:
                raise ValueError('Quiet hours; leave the notice queued.')
            notice = self.db.execute('SELECT * FROM task_notices WHERE id=?', (notice_id,)).fetchone()
            if not notice or notice['status'] != 'pending' or stamp(notice['due']) > now:
                raise ValueError('Notice is not due or is already claimed.')
            allowed_kinds = {'assignment'} | {f'{h}h' for h in policy.get('task_reminder_hours', [24])}
            if notice['kind'] not in allowed_kinds:
                raise ValueError('Notice cadence is no longer authorized.')
            assignment = self.db.execute('SELECT * FROM assignments WHERE id=?', (notice['assignment_id'],)).fetchone()
            task = self.db.execute('SELECT * FROM tasks WHERE id=?', (assignment['task_id'],)).fetchone()
            t = json.loads(task['payload'])
            v = json.loads(self.db.execute('SELECT payload FROM volunteers WHERE id=?', (assignment['volunteer_id'],)).fetchone()[0])
            if assignment['status'] != 'assigned' or task['status'] != 'open' or now >= stamp(t['start']):
                raise ValueError('Assignment is inactive or already started.')
            if assignment['policy_hash'] != digest(policy) or t['category'] not in policy['allowed_task_categories'] or not self._eligible(v, t, policy):
                raise ValueError('Reconcile assignment with current standing instructions and roster.')
            message = json.loads(notice['message'])
            if message['sender'] != policy['sender'] or message['to'] != [v['email']]:
                raise ValueError('The sending account or volunteer address changed; reconcile the notice.')
            self._check_communication_budget(now)
            self._check_contacts(message, now)
            self._record_contacts('task', notice_id, message, now)
            self.db.execute("UPDATE task_notices SET status='sending' WHERE id=?", (notice_id,))
            self.log('task_notice_claim', notice_id, {'policy_hash': digest(policy)}, now)
        return {'id': notice_id, 'message': message, 'instruction': 'Send exactly once through the configured sender; record the real provider receipt.'}

    def task_receipt(self, notice_id, outcome, provider_id, now=None):
        if outcome not in ('sent', 'failed', 'uncertain'):
            raise ValueError('Unknown delivery outcome.')
        required(provider_id, 'provider receipt or error reference')
        with self.db:
            changed = self.db.execute("UPDATE task_notices SET status=?,receipt=? WHERE id=? AND status IN ('sending','uncertain')", (outcome, provider_id, notice_id)).rowcount
            if changed != 1:
                raise ValueError('No outstanding delivery to reconcile.')
            self.log('task_notice_' + outcome, notice_id, {'receipt': provider_id}, stamp(now))
        return {'id': notice_id, 'status': outcome}

    def decline_task(self, assignment_id, volunteer_id, authority, now=None):
        required(authority, 'verified volunteer response reference')
        now = stamp(now)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT * FROM assignments WHERE id=?', (assignment_id,)).fetchone()
            if not row or row['volunteer_id'] != volunteer_id or row['status'] != 'assigned':
                raise ValueError('No active assignment for this volunteer.')
            self.db.execute("UPDATE assignments SET status='declined' WHERE id=?", (assignment_id,))
            self.db.execute("UPDATE task_notices SET status='cancelled' WHERE assignment_id=? AND status='pending'", (assignment_id,))
            from .signups import promote_waitlist
            offered = promote_waitlist(self, row['task_id'], now)
            self.log('task_declined', assignment_id, {'authority': authority}, now)
        return {'assignment_id': assignment_id, 'status': 'declined',
                'next': 'Waitlist replacement offered; participation is not confirmed.' if offered else 'Run delegate for automatic tasks; signup slots require an eligible signup or waitlisted participant.'}

    def overdue_tasks(self, now=None):
        now = stamp(now)
        overdue = []
        for row in self.db.execute("SELECT id,payload FROM tasks WHERE status='open'"):
            task = json.loads(row['payload'])
            if stamp(task['end']) < now:
                assignment_count = self.db.execute("SELECT count(*) FROM assignments WHERE task_id=? AND status='assigned'", (row['id'],)).fetchone()[0]
                overdue.append({'task_id': row['id'], 'title': task['title'], 'ended_at': task['end'],
                                'active_assignments': assignment_count, 'status': 'overdue_unresolved',
                                'next': 'Verify completion, cancel, or record follow-up; capacity remains reserved until an explicit lifecycle transition.'})
        return {'overdue': sorted(overdue, key=lambda item: (item['ended_at'], item['task_id']))}

    def follow_up_task(self, task_id, outcome, authority, note, now=None):
        required(authority, 'verified follow-up reference'); required(note, 'follow-up outcome note')
        if outcome not in ('still_open', 'completed', 'cancelled'):
            raise ValueError('Choose still_open, completed, or cancelled; never infer completion.')
        if outcome in ('completed', 'cancelled'):
            return self.close_task(task_id, outcome, authority, now=now)
        with self.db:
            if not self.db.execute("SELECT 1 FROM tasks WHERE id=? AND status='open'", (task_id,)).fetchone():
                raise ValueError('No open task with that ID.')
            self.log('task_follow_up', task_id, {'outcome': outcome, 'authority': authority, 'note': note}, stamp(now))
        return {'task_id': task_id, 'status': 'open', 'capacity_released': False}

    def close_task(self, task_id, status, authority, now=None):
        if status not in ('completed', 'cancelled'):
            raise ValueError('Choose completed or cancelled.')
        required(authority, 'completion or cancellation reference')
        with self.db:
            changed = self.db.execute("UPDATE tasks SET status=? WHERE id=? AND status='open'", (status, task_id)).rowcount
            if not changed:
                raise ValueError('No open task with that ID.')
            self.db.execute("UPDATE task_notices SET status='cancelled' WHERE status='pending' AND assignment_id IN (SELECT id FROM assignments WHERE task_id=?)", (task_id,))
            self.log('task_' + status, task_id, {'authority': authority}, stamp(now))
        return {'task_id': task_id, 'status': status}

    def record_participation(self, **request):
        from .participation import record
        return record(self, **request)

    def participation_history(self, record_id):
        from .participation import history
        return history(self, record_id)

    def weekly_brief(self, week_start):
        from .reporting import weekly
        return weekly(self, week_start)

    def allocation_report(self, task_id=None):
        rows = self.db.execute("SELECT at,object_id,detail FROM audit WHERE action='task_delegated' ORDER BY id").fetchall()
        decisions = []
        for row in rows:
            if task_id is not None and row['object_id'] != task_id:
                continue
            detail = json.loads(row['detail'])
            decisions.append({'task_id': row['object_id'], 'at': row['at'],
                              'assignment_id': detail['assignment_id'],
                              'selection': detail.get('selection'),
                              'explanation': 'Historical selection evidence unavailable.' if not detail.get('selection') else detail['selection']['order']})
        counts = [self.db.execute("SELECT count(*) FROM assignments WHERE volunteer_id=? AND status='assigned'", (row[0],)).fetchone()[0]
                  for row in self.db.execute('SELECT id FROM volunteers')]
        return {'decisions': decisions,
                'distribution': {'recorded_volunteers': len(counts), 'assigned_total': sum(counts),
                                 'minimum': min(counts, default=0), 'maximum': max(counts, default=0)},
                'scope': 'Trusted owner report. Descriptive assignment counts include completed work; not attendance, reliability, personal worth or a fairness guarantee. Different eligibility and availability affect distribution.'}

    def add_shift(self, shift, authority, now=None):
        from .shifts import add_shift
        return add_shift(self, shift, authority, now)

    def shift_status(self, shift_id):
        from .shifts import status
        return status(self, shift_id)
