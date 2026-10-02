"""Reproducible aggregate exports from explicit participation and coordination."""
from datetime import date, timedelta
import json
from zoneinfo import ZoneInfo
from .core import stamp


def weekly(coordinator, week_start):
    start=date.fromisoformat(week_start);end=start+timedelta(days=7);upcoming_end=end+timedelta(days=7)
    programs={}
    for row in coordinator.db.execute("SELECT value FROM settings WHERE key LIKE 'participation:%' ORDER BY key"):
        item=json.loads(row[0])
        if not start <= date.fromisoformat(item['on']) < end: continue
        group=programs.setdefault(item['program'],{'confirmed_participations':0,'confirmed_absences':0,'confirmed_minutes':0,'missing':0,'disputed':0})
        if item['status']=='confirmed':
            group['confirmed_participations' if item['attended'] else 'confirmed_absences']+=1
            group['confirmed_minutes']+=item['minutes']
        else:group[item['status']]+=1
    zone=ZoneInfo(coordinator.profile()['timezone'])
    upcoming={'events':0,'open_tasks':0,'unassigned_tasks':0,'reserved_offer_tasks':0}
    for row in coordinator.db.execute('SELECT start FROM events WHERE cancelled=0'):
        if end <= stamp(row[0]).astimezone(zone).date() < upcoming_end:upcoming['events']+=1
    for row in coordinator.db.execute("SELECT id,payload FROM tasks WHERE status='open'"):
        item=json.loads(row['payload'])
        if end <= stamp(item['start']).astimezone(zone).date() < upcoming_end:
            upcoming['open_tasks']+=1
            statuses = {r[0] for r in coordinator.db.execute(
                'SELECT status FROM assignments WHERE task_id=?', (row['id'],))}
            if 'assigned' not in statuses:
                upcoming['reserved_offer_tasks' if 'offered' in statuses else 'unassigned_tasks'] += 1
    exceptions={'draft':0,'failed':0,'unknown':0}
    unavailable=[]
    for table in ('reminders','task_notices','corrections'):
        if not coordinator.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
            unavailable.append(table);continue
        for row in coordinator.db.execute(f'SELECT status,count(*) FROM {table} GROUP BY status'):
            key='unknown' if row[0] in ('sending','uncertain') else row[0]
            if key in exceptions:exceptions[key]+=row[1]
    return {'period':{'start':start.isoformat(),'end_exclusive':end.isoformat()},
            'programs':dict(sorted(programs.items())), 'outcome_records_supplied':bool(programs),
            'upcoming_period':{'start':end.isoformat(),'end_exclusive':upcoming_end.isoformat()},
            'upcoming':upcoming,'unresolved_delivery':exceptions, 'unavailable_components':unavailable,
            'audit_revision':coordinator.db.execute('SELECT coalesce(max(id),0) FROM audit').fetchone()[0],
            'limits':'Confirmed participations count person/activity records, not unique people. Missing/disputed records and unsupplied outcomes are not zero attendance. Notices and offers are not outcomes.'}
