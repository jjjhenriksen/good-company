"""The explicitly selected local reservation ledger; no external booking claims."""
import json
from datetime import timedelta
from .core import digest, iso, required_time, stamp
from .modules import fields, text

RESOURCE_FIELDS = {'id', 'name', 'owner', 'capacity', 'availability', 'setup_minutes', 'teardown_minutes'}
BOOKING_FIELDS = {'id', 'resource_id', 'requester', 'start', 'end', 'quantity', 'event_id'}


def interval(start, end):
    start, end = required_time(start, 'start time'), required_time(end, 'end time')
    if not start < end:
        raise ValueError('The end must follow the start.')
    return start, end


def add_resource(c, resource, actor, authority, now=None):
    p = c._module_owner('resources', actor)
    r = fields(resource, RESOURCE_FIELDS, RESOURCE_FIELDS)
    for key in ('id', 'name', 'owner'):
        r[key] = text(r[key], key)
    if r['owner'] not in p['owners'] or r['owner'] != actor:
        raise ValueError('The named custodian must register their own resource.')
    if type(r['capacity']) is not int or not 1 <= r['capacity'] <= 10000:
        raise ValueError('Capacity must be 1–10000 units.')
    for key in ('setup_minutes', 'teardown_minutes'):
        if type(r[key]) is not int or not 0 <= r[key] <= 1440:
            raise ValueError('Resource buffers must be 0–1440 minutes.')
    if not isinstance(r['availability'], list) or not r['availability']:
        raise ValueError('Supply custodian-authorized availability intervals.')
    for window in r['availability']:
        fields(window, {'start', 'end'}, {'start', 'end'})
        interval(window['start'], window['end'])
    r.update(record_type='resource', viewers=[actor], source=p['source'])
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        p = c._module_owner('resources', actor)
        old = c.db.execute("SELECT payload,status FROM module_records WHERE module='resources' AND id=?", (r['id'],)).fetchone()
        if old:
            if old['status'] == 'expired' or json.loads(old['payload']) != r:
                raise ValueError('Registered resources are immutable; register a replacement with a new ID.')
            return {'id': r['id'], 'status': 'available', 'replayed': True}
        return c._save_record('resources', r['id'], r, 'available', c._expiry(p, now), authority, now)


def _resource(c, resource_id, actor, now):
    p = c._module_policy('resources', actor)
    r = c._record('resources', resource_id, now=now)['payload']
    if r.get('record_type') != 'resource':
        raise ValueError('Use a registered resource ID.')
    if r['owner'] not in p['owners']:
        raise ValueError('The registered custodian is no longer authorized; reconcile existing reservations.')
    return r


def _remaining(c, r, start, end):
    marks = []
    for row in c.db.execute("SELECT payload FROM module_records WHERE module='resources' AND status='booked'"):
        b = json.loads(row[0])
        if b.get('record_type') != 'booking' or b['resource_id'] != r['id']:
            continue
        left, right = stamp(b['blocked_start']), stamp(b['blocked_end'])
        if left < end and start < right:
            marks += [(max(start, left), b['quantity']), (min(end, right), -b['quantity'])]
    load, peak = 0, 0
    for _, delta in sorted(marks, key=lambda point: (point[0], point[1])):
        load += delta
        peak = max(peak, load)
    return r['capacity'] - peak


def _window(r, start, end):
    start, end = interval(start, end)
    left, right = start - timedelta(minutes=r['setup_minutes']), end + timedelta(minutes=r['teardown_minutes'])
    if not any(stamp(w['start']) <= left and right <= stamp(w['end']) for w in r['availability']):
        raise ValueError('The booking and its buffers must fit authorized availability.')
    return start, end, left, right


def resource_availability(c, resource_id, start, end, actor, now=None):
    now = stamp(now)
    r = _resource(c, resource_id, actor, now)
    _, _, left, right = _window(r, start, end)
    return {'resource_id': resource_id, 'available_units': _remaining(c, r, left, right),
            'source': 'good-company-ledger', 'observed_at': iso(now),
            'scope': 'Advisory read; capacity is checked atomically when booking.'}


def book_resource(c, booking, actor, authority, now=None):
    p = c._module_policy('resources', actor)
    b = fields(booking, BOOKING_FIELDS, BOOKING_FIELDS - {'event_id'})
    for key in ('id', 'resource_id', 'requester'):
        b[key] = text(b[key], key)
    if b['requester'] not in p['people']:
        raise ValueError('The requester must be enrolled in this booking workflow.')
    if type(b['quantity']) is not int or b['quantity'] < 1:
        raise ValueError('Request a positive integer quantity.')
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        p = c._module_policy('resources', actor)
        r = _resource(c, b['resource_id'], actor, now)
        if actor not in (b['requester'], r['owner']):
            raise ValueError('Only the requester or resource custodian can book.')
        start, end, left, right = _window(r, b['start'], b['end'])
        b.update(start=iso(start), end=iso(end))
        fingerprint = digest(b)
        old = c.db.execute("SELECT payload,status FROM module_records WHERE module='resources' AND id=?", (b['id'],)).fetchone()
        if old:
            stored = json.loads(old['payload'])
            if stored.get('request_hash') != fingerprint or old['status'] != 'booked':
                raise ValueError('This booking ID has already been used; reconcile its original outcome.')
            return {'id': b['id'], 'status': 'booked', 'receipt': stored['receipt'], 'replayed': True}
        resource_expiry = c._record('resources', b['resource_id'], now=now)['expires_at']
        if start < now or right >= min(stamp(c._expiry(p, now)), stamp(resource_expiry)):
            raise ValueError('Booking must be in the future and within the retention period.')
        if _remaining(c, r, left, right) < b['quantity']:
            raise ValueError('Insufficient resource capacity in the authorized ledger.')
        receipt = 'good-company-ledger:' + digest(['reserve', b['id'], fingerprint])
        b.update(record_type='booking', subject=b['requester'], owner=r['owner'],
                 viewers=list(dict.fromkeys([b['requester'], r['owner']])), source=p['source'],
                 blocked_start=iso(left), blocked_end=iso(right), request_hash=fingerprint,
                 receipt=receipt, **c._event_binding(b.get('event_id')))
        result = c._save_record('resources', b['id'], b, 'booked', c._expiry(p, now), authority, now)
        return result | {'receipt': receipt, 'scope': 'Confirmed in the selected local ledger; no external reservation or payment.'}


def cancel_booking(c, booking_id, actor, authority, now=None):
    now = stamp(now)
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        row = c._record('resources', booking_id, actor, now)
        b = row['payload']
        if b.get('record_type') != 'booking' or actor not in (b['subject'], b['owner']):
            raise ValueError('Only the requester or custodian can release a booking.')
        if row['status'] == 'cancelled':
            return {'id': booking_id, 'status': 'cancelled', 'receipt': b['release_receipt'], 'replayed': True}
        if row['status'] != 'booked':
            raise ValueError('Only a booked reservation can be released.')
        b['release_receipt'] = 'good-company-ledger:' + digest(['release', booking_id, b['receipt']])
        return c._save_record('resources', booking_id, b, 'cancelled', row['expires_at'], authority, now,
                              row['revision'] + 1) | {'receipt': b['release_receipt']}
