"""Consent-scoped arrangements with separate confirmation and actual checks."""
import json
from .core import digest, iso, stamp
from .modules import fields, text

REQUEST_FIELDS = {'id', 'event_id', 'requester', 'owner', 'service_owner', 'arrangement', 'consent', 'share_with'}


def request_accessibility(c, request, actor, authority, now=None):
    r = fields(request, REQUEST_FIELDS, REQUEST_FIELDS)
    for key in REQUEST_FIELDS - {'share_with'}:
        r[key] = text(r[key], key, 1500 if key == 'arrangement' else 200)
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        p = c._module_policy('accessibility', actor)
        if actor != r['requester'] or r['owner'] not in p['owners'] or r['service_owner'] not in p['people']:
            raise ValueError('Verify the requester, responsible coordinator and service owner.')
        sharing = r['share_with']
        if not isinstance(sharing, list) or set(sharing) != {r['owner'], r['service_owner']} or len(sharing) != len(set(sharing)):
            raise ValueError('Record explicit consent to share with the named coordinator and service owner only.')
        r.update(subject=r['requester'], source=p['source'], viewers=list(dict.fromkeys([actor] + sharing)),
                 **c._event_binding(r['event_id']))
        old = c.db.execute("SELECT * FROM module_records WHERE module='accessibility' AND id=?", (r['id'],)).fetchone()
        fingerprint = digest(r)
        if old:
            if json.loads(old['payload']).get('request_hash') != fingerprint or old['status'] == 'withdrawn':
                raise ValueError('This request ID has been used; reconcile it or use a new consented request.')
            c._record('accessibility', r['id'], actor, now)
            return {'id': r['id'], 'status': old['status'], 'replayed': True}
        r['request_hash'] = fingerprint
        return c._save_record('accessibility', r['id'], r, 'requested', c._expiry(p, now), authority, now)


def update_accessibility(c, request_id, action, actor, evidence, authority, now=None):
    text(evidence, 'actual operation evidence reference')
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        row = c._record('accessibility', request_id, actor, now)
        r, p = row['payload'], c._module_policy('accessibility', actor)
        current = row['status']
        if current == 'withdrawn':
            raise ValueError('A withdrawn request cannot be restored by another operation.')
        if action == 'withdraw':
            if actor != r['subject']:
                raise ValueError('Only the verified requester can withdraw consent.')
            r = {key: r[key] for key in ('id', 'subject', 'owner', 'source')}
            r['viewers'] = list(dict.fromkeys([r['subject'], r['owner']]))
            status = 'withdrawn'
        else:
            if r['owner'] not in p['owners']:
                raise ValueError('The responsible coordinator is no longer authorized.')
            if action == 'recheck':
                if actor != r['owner']:
                    raise ValueError('Only the responsible coordinator can restart checking.')
                r.update(c._event_binding(r['event_id']))
                r.pop('confirmation', None); r.pop('verification', None)
                status = 'acknowledged'
            else:
                if not c._event_valid(r):
                    raise ValueError('The event changed; recheck arrangements against its current revision.')
                if action == 'acknowledge' and current == 'requested' and actor == r['owner']:
                    status = 'acknowledged'
                elif action == 'arrange' and current == 'acknowledged' and actor == r['service_owner']:
                    r['confirmation'] = {'evidence_hash': digest(evidence), 'by': actor, 'at': iso(now)}
                    status = 'arranged'
                elif action == 'verify' and current == 'arranged' and actor == r['owner']:
                    if digest(evidence) == r['confirmation']['evidence_hash']:
                        raise ValueError('Verification requires evidence of an actual check, separate from the service promise.')
                    r['verification'] = {'evidence_hash': digest(evidence), 'by': actor, 'at': iso(now)}
                    status = 'verified'
                elif action == 'unavailable' and actor in (r['owner'], r['service_owner']):
                    r.pop('confirmation', None); r.pop('verification', None)
                    status = 'unavailable'
                else:
                    raise ValueError('This action requires the responsible actor and the preceding workflow state.')
        return c._save_record('accessibility', request_id, r, status, row['expires_at'], authority, now,
                              row['revision'] + 1)
