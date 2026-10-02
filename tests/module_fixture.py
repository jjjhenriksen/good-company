"""Fictional optional-workflow remit, shared by behavioral acceptance tests."""
from datetime import datetime, timezone
from pathlib import Path
import json
from good_company.modules import ModuleCoordinator
from good_company.core import digest

NOW = datetime(2026, 10, 1, 17, tzinfo=timezone.utc)


def policy(source='good-company-ledger'):
    return {'enabled': True, 'owners': ['owner'],
            'people': {'owner': {'email': 'owner@example.invalid'}, 'alex': {'email': 'alex@example.invalid'},
                       'sam': {'email': 'sam@example.invalid'}, 'service': {}},
            'source': source, 'retention_days': 30,
            'notice_recipients': ['owner@example.invalid', 'alex@example.invalid', 'sam@example.invalid']}


def coordinator(path, module='resources', source='good-company-ledger'):
    c = ModuleCoordinator(path)
    root = Path(__file__).resolve().parents[1]
    c.configure(json.loads((root / 'examples/profile.json').read_text())['profile'])
    remit = json.loads((root / 'examples/autonomy.json').read_text())['policy']
    remit['allowed_recipients'].append('owner@example.invalid')
    c.configure_autonomy(remit, 'fictional standing remit', now=NOW)
    c.configure_module(module, policy(source), 'fictional module remit', now=NOW)
    return c


def resource(capacity=1, buffer=15):
    return {'id': 'projector', 'name': 'Fictional projector', 'owner': 'owner', 'capacity': capacity,
            'availability': [{'start': '2026-10-02T08:00:00Z', 'end': '2026-10-02T20:00:00Z'}],
            'setup_minutes': buffer, 'teardown_minutes': buffer}


def booking(record_id='booking-one', requester='alex', start='2026-10-02T10:00:00Z', end='2026-10-02T11:00:00Z'):
    return {'id': record_id, 'resource_id': 'projector', 'requester': requester,
            'start': start, 'end': end, 'quantity': 1}


def event_snapshot(location='Fictional hall'):
    return {'calendar': 'demo-events-only', 'complete': True, 'window_start': '2026-10-01T00:00:00Z',
            'window_end': '2026-10-15T00:00:00Z', 'checked_at': NOW.isoformat(),
            'events': [{'id': 'event-one', 'title': 'Fictional event', 'source': 'fictional://calendar',
                        'start': '2026-10-02T10:00:00Z', 'end': '2026-10-02T11:00:00Z',
                        'location': location, 'status': 'confirmed'}]}


def access_request():
    return {'id': 'captions', 'event_id': digest(['demo-events-only', 'event-one'])[:24], 'requester': 'alex', 'owner': 'owner',
            'service_owner': 'service', 'arrangement': 'Live captions for the presentation',
            'consent': 'fictional requester consent to the named recipients and retention',
            'share_with': ['owner', 'service']}


def checklist():
    return {'id': 'consent-form', 'title': 'Fictional event consent', 'subject': 'alex', 'owner': 'owner',
            'form_url': 'https://example.invalid/consent', 'form_version': 'v1',
            'due': '2026-10-02T16:00:00Z', 'source': 'fictional-document-register',
            'consent': 'fictional status-only consent and reminder remit'}
