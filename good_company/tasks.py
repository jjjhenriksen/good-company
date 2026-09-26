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
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS volunteers(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(
          id TEXT PRIMARY KEY, task_id TEXT NOT NULL, volunteer_id TEXT NOT NULL,
          status TEXT NOT NULL, policy_hash TEXT NOT NULL,
          UNIQUE(task_id, volunteer_id));
        CREATE TABLE IF NOT EXISTS task_notices(
          id TEXT PRIMARY KEY, assignment_id TEXT NOT NULL, kind TEXT NOT NULL,
          due TEXT NOT NULL, status TEXT NOT NULL, message TEXT NOT NULL, receipt TEXT,
          UNIQUE(assignment_id, kind));
        ''')

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
        if not isinstance(t.get('required_skills'), dict) or any(type(n) is not int or not 1 <= n <= 3 for n in t['required_skills'].values()):
            raise ValueError('required_skills must map skills to minimum proficiency 1–3.')
        if not isinstance(t.get('preferred_skills'), list):
            raise ValueError('preferred_skills must be a list.')
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
          JOIN assignments a ON a.task_id=t.id WHERE a.volunteer_id=? AND a.status='assigned'
          AND t.status='open' AND t.id<>?''', (volunteer_id, excluding or ''))]

    def _eligible(self, v, t, policy):
        workload = self._workload(v['id'], t['id'])
        if not v['accepts_delegation'] or v['email'] not in policy['allowed_recipients']:
            return False
        if t['category'] in v['avoid_categories'] or not set(t['eligible_roles']) & set(v['roles']):
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
        date = stamp(t['start']).astimezone(ZoneInfo(self.profile()['timezone'])).strftime('%A, %B %-d at %-I:%M %p %Z')
        prefix = 'Your task' if kind == 'assignment' else 'Task reminder'
        message = {'sender': policy['sender'], 'to': [v['email']], 'bcc': [],
                   'subject': f'{prefix}: {t["title"]}',
                   'body': f'Hi {v["name"]},\n\n{t["title"]}\nWhen: {date}\n\nThis is within the work you agreed to help with. If your availability has changed, reply and I will find another arrangement.\n\n{self.profile()["signoff"]}'}
        self.db.execute("""INSERT INTO task_notices VALUES(?,?,?,?,'pending',?,NULL)
          ON CONFLICT(id) DO UPDATE SET message=excluded.message,status='pending'
          WHERE task_notices.status IN ('pending','cancelled')""",
                        (aid, assignment_id, kind, iso(due), json.dumps(message)))

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
                if stamp(t['start']) <= now:
                    continue
                if t['category'] not in policy['allowed_task_categories']:
                    exceptions.append({'task_id': t['id'], 'reason': 'Task category is outside standing instructions.'})
                    continue
                existing = self.db.execute("SELECT * FROM assignments WHERE task_id=? AND status='assigned'", (t['id'],)).fetchone()
                if existing:
                    v = next((v for v in volunteers if v['id'] == existing['volunteer_id']), None)
                    if not v or not self._eligible(v, t, policy):
                        exceptions.append({'task_id': t['id'], 'reason': 'An existing assignment needs reconciliation after availability or role changed.'})
                        continue
                    assignment_id = existing['id']
                    self.db.execute('UPDATE assignments SET policy_hash=? WHERE id=?', (digest(policy), assignment_id))
                    self._notice(assignment_id, t, v, 'assignment', now, policy)
                else:
                    declined = {r[0] for r in self.db.execute("SELECT volunteer_id FROM assignments WHERE task_id=? AND status='declined'", (t['id'],))}
                    candidates = [v for v in volunteers if v['id'] not in declined and self._eligible(v, t, policy)]
                    if not candidates:
                        exceptions.append({'task_id': t['id'], 'reason': 'No eligible, available volunteer has capacity.'})
                        continue
                    def rank(v):
                        matches = sum(v['skills'].get(s, 0) for s in t['preferred_skills'])
                        preference = int(t['category'] in v['preferred_categories'])
                        return (-matches, -preference, len(self._workload(v['id'])), v['id'])
                    v = sorted(candidates, key=rank)[0]
                    assignment_id = digest([t['id'], v['id']])[:24]
                    self.db.execute("INSERT INTO assignments VALUES(?,?,?,'assigned',?)", (assignment_id, t['id'], v['id'], digest(policy)))
                    self._notice(assignment_id, t, v, 'assignment', now, policy)
                    self.log('task_delegated', t['id'], {'assignment_id': assignment_id, 'volunteer_id': v['id']}, now)
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
        with self.db:
            row = self.db.execute('SELECT * FROM assignments WHERE id=?', (assignment_id,)).fetchone()
            if not row or row['volunteer_id'] != volunteer_id or row['status'] != 'assigned':
                raise ValueError('No active assignment for this volunteer.')
            self.db.execute("UPDATE assignments SET status='declined' WHERE id=?", (assignment_id,))
            self.db.execute("UPDATE task_notices SET status='cancelled' WHERE assignment_id=? AND status='pending'", (assignment_id,))
            self.log('task_declined', assignment_id, {'authority': authority}, stamp(now))
        return {'assignment_id': assignment_id, 'status': 'declined', 'next': 'Run delegate to find another eligible volunteer.'}

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
