"""Minimal donor/beneficiary follow-up backed by an owner-selected register.

Imports record source observations, never payments, tax receipts, eligibility,
case management or source writes. JSON-register integration is explicit and
read-only; it is not presented as a connected CRM or a live subscription.
"""
import json
import os
from pathlib import Path
import re
import stat
from datetime import timedelta
from .core import digest, iso, required_time, stamp
from .modules import fields, text

RELATION_FIELDS = {'id', 'kind', 'subject', 'owner', 'external_id', 'source', 'purpose', 'consent'}
OBSERVATION_FIELDS = {'source', 'external_id', 'kind', 'state', 'version', 'checked_at', 'evidence', 'amount_minor', 'currency'}


def add_relationship(c, record, actor, authority, now=None):
    r = fields(record, RELATION_FIELDS, RELATION_FIELDS)
    for key in RELATION_FIELDS:
        r[key] = text(r[key], key)
    if r['kind'] not in ('donor', 'beneficiary'):
        raise ValueError('Choose donor or beneficiary; retail sales are not donations.')
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        p = c._module_owner('relationships', actor)
        if actor != r['owner'] or r['subject'] not in p['people'] or r['source'] != p['source']:
            raise ValueError('Supply the assigned owner, separate participant consent and selected register.')
        r['viewers'] = list(dict.fromkeys([r['subject'], r['owner']]))
        fingerprint = digest(r)
        old = c.db.execute("SELECT * FROM module_records WHERE module='relationships' AND id=?", (r['id'],)).fetchone()
        if old:
            if json.loads(old['payload']).get('request_hash') != fingerprint or old['status'] == 'withdrawn':
                raise ValueError('This relationship ID has been used; reconcile its consented record.')
            c._record('relationships', r['id'], actor, now)
            return {'id': r['id'], 'status': old['status'], 'replayed': True}
        for row in c.db.execute("SELECT payload FROM module_records WHERE module='relationships' AND status NOT IN ('expired','withdrawn')"):
            old = json.loads(row[0])
            if old['source'] == r['source'] and old['external_id'] == r['external_id']:
                raise ValueError('This external record is already bound; do not create a duplicate relationship.')
        r['request_hash'] = fingerprint
        return c._save_record('relationships', r['id'], r, 'active', c._expiry(p, now), authority, now)


def _observe(c, record_id, snapshot, actor, authority, now):
    s = fields(snapshot, OBSERVATION_FIELDS, OBSERVATION_FIELDS - {'amount_minor', 'currency'})
    for key in OBSERVATION_FIELDS - {'checked_at', 'amount_minor', 'currency'}:
        s[key] = text(s[key], key)
    checked = required_time(s['checked_at'], 'register observation time')
    if not timedelta(0) <= now - checked <= timedelta(minutes=15):
        raise ValueError('Use a current register observation, no more than 15 minutes old.')
    row = c._record('relationships', record_id, actor, now)
    r, p = row['payload'], c._module_owner('relationships', actor)
    if actor != r['owner'] or row['status'] == 'withdrawn':
        raise ValueError('Only the assigned owner may reconcile an active consented relationship.')
    if (s['source'], s['external_id'], s['kind']) != (r['source'], r['external_id'], r['kind']) or s['source'] != p['source']:
        raise ValueError('The source observation is outside this exact relationship binding.')
    states = {'donor': {'pledged': 'pledged', 'recorded': 'source_recorded'},
              'beneficiary': {'requested': 'service_requested', 'confirmed': 'source_confirmed'}}
    if s['state'] not in states[r['kind']]:
        raise ValueError('This source state is unsupported; sales, payments and case decisions are excluded.')
    if ('amount_minor' in s) != ('currency' in s):
        raise ValueError('An observed donor amount needs both minor units and currency.')
    if 'amount_minor' in s:
        if (r['kind'] != 'donor' or type(s['amount_minor']) is not int or not 0 <= s['amount_minor'] <= 10**12
                or not isinstance(s['currency'], str) or not re.fullmatch('[A-Z]{3}', s['currency'])):
            raise ValueError('Only a nonnegative donor register amount and supplied three-letter currency are supported.')
    content = {key: value for key, value in s.items() if key not in ('checked_at', 'evidence')}
    previous = r.get('observation')
    history = r.get('source_versions', {})
    if previous:
        if checked < stamp(previous['checked_at']):
            raise ValueError('The observation predates the reconciled register state.')
        if s['version'] == previous['version']:
            if digest(content) != previous['content_hash']:
                raise ValueError('A register version cannot describe conflicting records.')
            return {'id': record_id, 'status': row['status'], 'revision': row['revision'], 'replayed': True}
        if s['version'] in history:
            raise ValueError('A previously superseded source version cannot be replayed as a new observation.')
    if len(history) >= 1000:
        raise ValueError('Reconcile or replace this record after the supported source-history limit.')
    r['source_versions'] = history | {s['version']: digest(content)}
    r['observation'] = content | {'checked_at': iso(checked), 'content_hash': digest(content),
                                 'evidence_hash': digest(s['evidence'])}
    return c._save_record('relationships', record_id, r, states[r['kind']][s['state']],
                          row['expires_at'], authority, now, row['revision'] + 1)


def sync_relationship(c, record_id, snapshot, actor, authority, now=None):
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        return _observe(c, record_id, snapshot, actor, authority, stamp(now))


def import_relationship_register(c, path, actor, authority, now=None):
    c._module_owner('relationships', actor)
    text(authority, 'owner-authorized register import')
    path = Path(path)
    # The configured host reads only the explicitly supplied private register.
    # No directory discovery, account discovery, network calls or source writes.
    with path.open('rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Use an owner-held private regular register file (0600).')
        raw = stream.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('The register exceeds the supported size.')
    data = fields(json.loads(raw), {'source', 'complete', 'records'}, {'source', 'complete', 'records'})
    if data['complete'] is not True or not isinstance(data['records'], list) or len(data['records']) > 1000:
        raise ValueError('Import a bounded complete register; absence never withdraws consent.')
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        p = c._module_owner('relationships', actor)
        if data['source'] != p['source']:
            raise ValueError('This is not the selected authoritative register.')
        seen, results = set(), []
        for entry in data['records']:
            entry = fields(entry, {'record_id', 'snapshot'}, {'record_id', 'snapshot'})
            record_id = text(entry['record_id'], 'bound relationship ID')
            if record_id in seen:
                raise ValueError('Duplicate relationship IDs in the register.')
            seen.add(record_id)
            results.append(_observe(c, record_id, entry['snapshot'], actor, authority, now))
        return {'imported': len(results), 'replayed': sum(bool(r.get('replayed')) for r in results),
                'scope': 'Read-only owner-selected register observations; no source update or live CRM subscription.'}
