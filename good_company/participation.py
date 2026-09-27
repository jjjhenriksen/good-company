"""Explicit trusted-operator outcomes, independent of assignments and notices."""
from datetime import date
import json
from .core import required, digest, stamp


def record(coordinator, activity_id, participant_id, program, on, status, attended, minutes,
           source, authority, expected_revision=0, now=None):
    for value,label in [(activity_id,'activity id'),(participant_id,'participant id'),(program,'program'),(source,'verified outcome source'),(authority,'reviewing authority')]:
        required(value,label)
    date.fromisoformat(on)
    if status not in ('confirmed','missing','disputed'):
        raise ValueError('Outcome status must be confirmed, missing or disputed.')
    if status=='confirmed':
        if type(attended) is not bool or type(minutes) is not int or not 0 <= minutes <= 1440:
            raise ValueError('Confirmed outcomes require attendance and 0–1440 verified minutes.')
        if not attended and minutes: raise ValueError('Absent participants cannot have confirmed service minutes.')
    elif attended is not None or minutes is not None:
        raise ValueError('Missing/disputed outcomes must not assert attendance or time.')
    if type(expected_revision) is not int or expected_revision < 0: raise ValueError('Supply the last observed revision.')
    record_id=digest([activity_id,participant_id])[:24]
    key='participation:'+record_id
    payload={'activity_id':activity_id,'participant_id':participant_id,'program':program,'on':on,'status':status,
             'attended':attended,'minutes':minutes,'source':source,'authority':authority,'revision':expected_revision+1}
    with coordinator.db:
        coordinator.db.execute('BEGIN IMMEDIATE')
        previous=coordinator.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        old=json.loads(previous[0]) if previous else None
        if (old['revision'] if old else 0)!=expected_revision:
            raise ValueError('Participation changed; review the current record before correcting it.')
        coordinator.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(payload)))
        coordinator.log('participation_recorded',record_id,{'previous':old,'current':payload},stamp(now))
    return {'record_id':record_id,'revision':payload['revision'],'status':status}


def history(coordinator, record_id):
    return {'record_id':record_id,'revisions':[{'at':row['at'],**json.loads(row['detail'])} for row in coordinator.db.execute(
        "SELECT at,detail FROM audit WHERE action='participation_recorded' AND object_id=? ORDER BY id",(record_id,))]}
