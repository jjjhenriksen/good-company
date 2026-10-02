"""Supplied document status/deadlines, never content verification or compliance."""
import json
from urllib.parse import urlsplit
from datetime import timedelta
from .core import digest, iso, required_time, stamp
from .modules import fields, text

ITEM_FIELDS = {'id', 'title', 'subject', 'owner', 'form_url', 'form_version', 'due', 'source', 'consent', 'event_id'}


def add_checklist(c, item, actor, authority, now=None):
    r = fields(item, ITEM_FIELDS, ITEM_FIELDS - {'event_id'})
    for key in ITEM_FIELDS - {'due', 'event_id'}:
        r[key] = text(r[key], key, 1000 if key == 'form_url' else 200)
    link = urlsplit(r['form_url'])
    if link.scheme != 'https' or not link.hostname or link.username or link.password:
        raise ValueError('Supply the official HTTPS form link without embedded credentials.')
    r['due'] = iso(required_time(r['due'], 'supplied deadline'))
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        p = c._module_owner('checklists', actor)
        if actor != r['owner'] or r['subject'] not in p['people'] or r['source'] != p['source']:
            raise ValueError('Verify the assigned custodian, consented participant and authoritative status source.')
        if stamp(r['due']) >= stamp(c._expiry(p, now)):
            raise ValueError('The supplied deadline must fit the selected retention period.')
        r.update(viewers=list(dict.fromkeys([r['subject'], r['owner']])), **c._event_binding(r.get('event_id')))
        fingerprint = digest(r)
        old = c.db.execute("SELECT * FROM module_records WHERE module='checklists' AND id=?", (r['id'],)).fetchone()
        if old:
            if json.loads(old['payload']).get('request_hash') != fingerprint or old['status'] == 'withdrawn':
                raise ValueError('This checklist ID has been used; update its status or supply a new item.')
            c._record('checklists', r['id'], actor, now)
            return {'id': r['id'], 'status': old['status'], 'replayed': True}
        r['request_hash'] = fingerprint
        return c._save_record('checklists', r['id'], r, 'missing', c._expiry(p, now), authority, now)


def update_checklist(c, item_id, action, actor, evidence, authority, due=None, form_version=None, now=None):
    text(evidence, 'verified submission or source observation')
    if action == 'withdraw':
        return c.withdraw_module_record('checklists', item_id, actor, authority, now=now)
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        row = c._record('checklists', item_id, actor, now)
        r, p = row['payload'], c._module_policy('checklists', actor)
        operation = digest([action, actor, evidence, due, form_version])
        if r.get('last_operation') == operation:
            return {'id': item_id, 'status': row['status'], 'revision': row['revision'], 'replayed': True}
        if row['status'] == 'withdrawn':
            raise ValueError('A withdrawn checklist requires a new consented item.')
        if action != 'change-deadline' and due is not None or action != 'replace-version' and form_version is not None:
            raise ValueError('Supply only fields relevant to the selected checklist action.')
        if action == 'withdraw':
            if actor != r['subject']:
                raise ValueError('Only the verified participant can withdraw their checklist consent.')
            r = {key: r[key] for key in ('id', 'subject', 'owner', 'source', 'viewers')}
            status = 'withdrawn'
        else:
            if r['owner'] not in p['owners']:
                raise ValueError('The assigned custodian changed; reconcile the requirement.')
            if action == 'recheck-event' and actor == r['owner']:
                if not r.get('event_id'):
                    raise ValueError('This checklist is not linked to an event.')
                r.update(c._event_binding(r['event_id']))
                r.pop('acknowledgment', None); r.pop('reported_submission', None)
                r['last_operation'] = operation
                return c._save_record('checklists', item_id, r, 'missing', row['expires_at'], authority, now, row['revision'] + 1)
            if not c._event_valid(r, now=now):
                raise ValueError('The event or assigned custodian changed; reconcile the requirement.')
            if action == 'report-submitted' and actor == r['subject'] and row['status'] == 'missing':
                r['reported_submission'] = {'evidence_hash': digest(evidence), 'at': iso(now)}
                status = 'reported_submitted'
            elif actor == r['owner']:
                if action == 'acknowledge':
                    r['acknowledgment'] = {'evidence_hash': digest(evidence), 'source': r['source'], 'at': iso(now)}
                    status = 'acknowledged'
                elif action == 'mark-missing':
                    r.pop('acknowledgment', None); r.pop('reported_submission', None)
                    status = 'missing'
                elif action == 'change-deadline':
                    deadline = required_time(due, 'new source-supplied deadline')
                    if deadline >= stamp(row['expires_at']):
                        raise ValueError('The new deadline must fit this record\'s retention.')
                    r['due'] = iso(deadline)
                    status = row['status']
                elif action == 'replace-version':
                    r['form_version'] = text(form_version, 'replacement source version')
                    r.pop('acknowledgment', None); r.pop('reported_submission', None)
                    status = 'missing'
                else:
                    raise ValueError('Unknown checklist action.')
            else:
                raise ValueError('This checklist action requires the participant or assigned custodian.')
        r['last_operation'] = operation
        return c._save_record('checklists', item_id, r, status, row['expires_at'], authority, now, row['revision'] + 1)


def plan_checklists(c, now=None):
    now = stamp(now)
    p = c._module_policy('checklists')
    created, exceptions = [], 0
    for row in c.db.execute("SELECT id,payload,expires_at FROM module_records WHERE module='checklists' AND status='missing'").fetchall():
        if stamp(row['expires_at']) <= now:
            continue
        r = json.loads(row['payload'])
        if required_time(r['due'], 'supplied deadline') - timedelta(days=1) > now:
            continue
        recipient = p['people'].get(r['subject'], {}).get('email')
        if not recipient or recipient not in p['notice_recipients']:
            continue
        try:
            notice = c.module_notice('checklists', row['id'], recipient, iso(now), r['owner'],
                                     'configured checklist reminder authority', now=now)
            if notice['status'] == 'pending':
                created.append(notice['id'])
        except ValueError:
            exceptions += 1
    return {'queued': list(dict.fromkeys(created)), 'exceptions': exceptions}
