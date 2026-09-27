"""Staffed shifts reuse individually constrained, atomically allocated task slots."""
import json
from pathlib import Path
import tempfile
from .core import required, stamp


def add_shift(coordinator, shift, authority, now=None):
    from .tasks import WorkCoordinator
    required(authority, 'shift authority')
    required(shift.get('id'), 'shift id'); required(shift.get('title'), 'shift title')
    slots = shift.get('slots')
    if not isinstance(slots, list) or not 1 <= len(slots) <= 100 or any(not isinstance(slot, dict) for slot in slots):
        raise ValueError('Supply 1–100 explicit staffing slots.')
    ids = [required(slot.get('id'), 'slot id') for slot in slots]
    if len(set(ids)) != len(ids): raise ValueError('Slot ids must be unique.')
    if shift.get('capacity') != len(slots): raise ValueError('Capacity must equal the explicit staffing slot count.')
    tasks = []
    with tempfile.TemporaryDirectory() as folder:
        candidate = WorkCoordinator(Path(folder)/'candidate.sqlite')
        try:
            coordinator.db.backup(candidate.db)
            for slot in slots:
                task = dict(slot, id=shift['id'] + ':' + slot['id'])
                candidate.add_task(task, authority, now=now)
                tasks.append(json.loads(candidate.db.execute('SELECT payload FROM tasks WHERE id=?',(task['id'],)).fetchone()[0]))
        finally: candidate.db.close()
    payload = {'id': shift['id'], 'title': shift['title'], 'capacity': len(tasks), 'task_ids': [t['id'] for t in tasks]}
    key = 'shift:' + shift['id']
    with coordinator.db:
        coordinator.db.execute('BEGIN IMMEDIATE')
        prior = coordinator.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        if prior:
            if json.loads(prior[0]) != payload: raise ValueError('Existing shifts are immutable; explicitly replace changed slots.')
            for task in tasks:
                row=coordinator.db.execute('SELECT payload FROM tasks WHERE id=?',(task['id'],)).fetchone()
                if not row or json.loads(row[0]) != task: raise ValueError('Existing shift requirements cannot change.')
            return payload
        if any(not coordinator._event_current(t) for t in tasks): raise ValueError('Linked event changed; refresh the shift before adding it.')
        for task in tasks:
            if coordinator.db.execute('SELECT 1 FROM tasks WHERE id=?',(task['id'],)).fetchone():
                raise ValueError('A shift slot collides with an existing task.')
        for task in tasks:
            coordinator.db.execute("INSERT INTO tasks VALUES(?,?,'open')",(task['id'],json.dumps(task)))
        coordinator.db.execute('INSERT INTO settings VALUES(?,?)',(key,json.dumps(payload)))
        coordinator.log('shift_added',shift['id'],{'authority':authority,'capacity':len(tasks)},stamp(now))
    return payload


def status(coordinator, shift_id):
    row = coordinator.db.execute('SELECT value FROM settings WHERE key=?',('shift:'+shift_id,)).fetchone()
    if not row: raise ValueError('Unknown shift.')
    shift = json.loads(row[0]); slots=[]
    for task_id in shift['task_ids']:
        task=coordinator.db.execute('SELECT status,payload FROM tasks WHERE id=?',(task_id,)).fetchone()
        assigned=coordinator.db.execute("SELECT count(*) FROM assignments WHERE task_id=? AND status='assigned'",(task_id,)).fetchone()[0]
        filled=task['status']=='open' and assigned==1
        slots.append({'task_id':task_id,'status':task['status'],'filled':filled,
                      'reason':None if filled or task['status']!='open' else 'Unfilled: allocation must satisfy recorded roles, qualifications, consent, availability and workload capacity.'})
    return {'shift_id':shift_id,'capacity':shift['capacity'],'filled':sum(s['filled'] for s in slots),
            'unfilled':sum(not s['filled'] and s['status']=='open' for s in slots),'slots':slots,
            'scope':'Allocation is not verified attendance or an accepted signup.'}
