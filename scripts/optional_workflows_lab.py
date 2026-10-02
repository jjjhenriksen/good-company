#!/usr/bin/env python3
"""Exercise all four optional workflows through the real CLI with fictional data.

Uses the real clock, a fresh private database and an owner-held JSON register.
No network, provider connection or email send occurs. This is command acceptance,
not live provider or nonprofit fulfillment evidence.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run():
    root = Path(__file__).resolve().parents[1]
    clock = datetime.now(timezone.utc)
    checks = []
    with tempfile.TemporaryDirectory(prefix='good-company-optional-lab-') as directory:
        database = Path(directory) / 'state.sqlite'

        def command(action, request, reject=False):
            result = subprocess.run([sys.executable, '-m', 'good_company.cli', '--db', str(database), action],
                                    input=json.dumps(request), capture_output=True, text=True, cwd=root)
            if reject:
                if result.returncode != 2 or 'error' not in json.loads(result.stderr):
                    raise AssertionError('Expected a structured domain refusal: ' + action)
                return
            if result.returncode:
                raise AssertionError('Command acceptance failed: ' + action)
            return json.loads(result.stdout)

        def verify(condition, name):
            if not condition:
                raise AssertionError('Acceptance check failed: ' + name)
            checks.append(name)

        command('configure', json.loads((root / 'examples/profile.json').read_text()))
        remit = json.loads((root / 'examples/autonomy.json').read_text())
        remit['policy']['allowed_recipients'].append('owner@example.invalid')
        command('configure-autonomy', remit)
        base = {'enabled': True, 'owners': ['owner'], 'retention_days': 30,
                'people': {'owner': {'email': 'owner@example.invalid'}, 'alex': {'email': 'alex@example.invalid'},
                           'sam': {'email': 'sam@example.invalid'}, 'service': {}},
                'notice_recipients': ['owner@example.invalid', 'alex@example.invalid', 'sam@example.invalid']}
        for module, source in [('resources', 'good-company-ledger'), ('accessibility', 'fictional-service-desk'),
                               ('checklists', 'fictional-document-register'), ('relationships', 'fictional-relationship-register')]:
            command('configure-module', {'module': module, 'policy': base | {'source': source}, 'authority': 'fictional owner remit'})

        start, end = clock + timedelta(days=2), clock + timedelta(days=2, hours=1)
        command('import-calendar', {'snapshot': {'calendar': 'demo-events-only', 'complete': True,
                'window_start': clock.isoformat(), 'window_end': (clock + timedelta(days=7)).isoformat(),
                'checked_at': clock.isoformat(), 'events': [{'id': 'event-one', 'title': 'Fictional event',
                    'start': start.isoformat(), 'end': end.isoformat(), 'source': 'fictional://calendar',
                    'location': 'Fictional hall', 'status': 'confirmed'}]}})
        event_id = command('events', {})[0]['id']
        command('add-resource', {'actor': 'owner', 'authority': 'fictional custodian', 'resource': {
                'id': 'projector', 'name': 'Fictional projector', 'owner': 'owner', 'capacity': 1,
                'setup_minutes': 15, 'teardown_minutes': 15, 'availability': [{
                    'start': (start - timedelta(hours=1)).isoformat(), 'end': (end + timedelta(hours=2)).isoformat()}]}})
        booking = {'id': 'booking-one', 'resource_id': 'projector', 'requester': 'alex', 'quantity': 1,
                   'start': start.isoformat(), 'end': end.isoformat(), 'event_id': event_id}
        request = {'booking': booking, 'actor': 'alex', 'authority': 'fictional verified request'}
        first = command('book-resource', request)
        verify(first['status'] == 'booked' and first['receipt'].startswith('good-company-ledger:'), 'resource-local-reservation-receipt')
        verify(command('book-resource', request)['receipt'] == first['receipt'], 'resource-idempotent-reservation')
        command('book-resource', request | {'booking': booking | {'id': 'conflict', 'requester': 'sam'}, 'actor': 'sam'}, reject=True)
        checks.append('resource-overlap-refused')
        verify(command('cancel-booking', {'booking_id': 'booking-one', 'actor': 'alex', 'authority': 'verified release'})['status'] == 'cancelled', 'resource-release-receipt')

        arrangement = {'id': 'captions', 'event_id': event_id, 'requester': 'alex', 'owner': 'owner',
                       'service_owner': 'service', 'arrangement': 'Fictional live captions',
                       'consent': 'fictional sharing and retention consent', 'share_with': ['owner', 'service']}
        command('request-accessibility', {'request': arrangement, 'actor': 'alex', 'authority': 'verified request'})
        command('update-accessibility', {'request_id': 'captions', 'action': 'verify', 'actor': 'owner', 'evidence': 'not arranged', 'authority': 'owner'}, reject=True)
        checks.append('accessibility-unarranged-verification-refused')
        for action, actor, evidence in [('acknowledge', 'owner', 'fictional coordinator acknowledgment'),
                                        ('arrange', 'service', 'fictional service confirmation'),
                                        ('verify', 'owner', 'fictional actual captions checked')]:
            result = command('update-accessibility', {'request_id': 'captions', 'action': action, 'actor': actor,
                                                       'evidence': evidence, 'authority': 'verified responsible actor'})
        verify(result['status'] == 'verified', 'accessibility-confirmation-and-check-separated')
        command('module-status', {'module': 'accessibility', 'record_id': 'captions', 'actor': 'sam'}, reject=True)
        checks.append('accessibility-other-team-view-refused')
        verify(command('withdraw-module-record', {'module': 'accessibility', 'record_id': 'captions', 'actor': 'alex', 'authority': 'verified withdrawal'})['status'] == 'withdrawn', 'accessibility-withdrawal')

        item = {'id': 'form-one', 'title': 'Fictional consent form', 'subject': 'alex', 'owner': 'owner',
                'form_url': 'https://example.invalid/form', 'form_version': 'v1', 'due': start.isoformat(),
                'source': 'fictional-document-register', 'consent': 'fictional status and reminder consent'}
        command('add-checklist', {'item': item, 'actor': 'owner', 'authority': 'fictional source requirements'})
        update = {'item_id': 'form-one', 'action': 'report-submitted', 'actor': 'alex', 'evidence': 'fictional participant report', 'authority': 'verified participant'}
        verify(command('update-checklist', update)['status'] == 'reported_submitted', 'checklist-report-is-not-acknowledgment')
        command('update-checklist', update | {'action': 'acknowledge'}, reject=True)
        checks.append('checklist-participant-cannot-acknowledge-source')
        verify(command('update-checklist', update | {'action': 'acknowledge', 'actor': 'owner', 'evidence': 'fictional actual register acknowledgment'})['status'] == 'acknowledged', 'checklist-authoritative-acknowledgment')

        relation = {'id': 'donor-one', 'kind': 'donor', 'subject': 'alex', 'owner': 'owner', 'external_id': 'external-donor',
                    'source': 'fictional-relationship-register', 'purpose': 'Fictional consented follow-up', 'consent': 'fictional separate donor consent'}
        command('add-relationship', {'record': relation, 'actor': 'owner', 'authority': 'verified separate consent'})
        observation = {'source': relation['source'], 'external_id': relation['external_id'], 'kind': 'donor', 'state': 'recorded',
                       'version': 'v1', 'checked_at': clock.isoformat(), 'evidence': 'fictional source observation'}
        command('sync-relationship', {'record_id': 'donor-one', 'snapshot': observation | {'state': 'retail_sale'}, 'actor': 'owner', 'authority': 'source observation'}, reject=True)
        checks.append('relationship-retail-sale-refused')
        register = Path(directory) / 'register.json'
        register.write_text(json.dumps({'source': relation['source'], 'complete': True, 'records': [{'record_id': 'donor-one', 'snapshot': observation}]}))
        register.chmod(0o600)
        original = register.read_bytes()
        request = {'path': str(register), 'actor': 'owner', 'authority': 'owner-selected read-only register'}
        verify(command('import-relationship-register', request)['imported'] == 1, 'relationship-private-register-import')
        verify(command('import-relationship-register', request)['replayed'] == 1 and register.read_bytes() == original, 'relationship-read-only-import-deduplication')
        verify('alex' not in json.dumps(command('module-summary', {})), 'aggregate-summary-omits-identities')
    return {'status': 'passed', 'scope': 'Fictional isolated command acceptance using the real clock.',
            'modules': 4, 'checks': checks, 'network_calls': 0, 'external_emails_sent': 0,
            'live_provider_evidence': False, 'real_nonprofit_fulfillment': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = run()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(report, stream, indent=2); stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
