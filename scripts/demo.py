#!/usr/bin/env python3
"""A credential-free demonstration of the real coordination engine, using fiction."""
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from good_company.core import Coordinator
root = Path(__file__).resolve().parents[1]
now = datetime.now(timezone.utc)
local = now.astimezone(ZoneInfo('America/Los_Angeles'))
event_start = (local + timedelta(days=8)).replace(hour=17, minute=30, second=0, microsecond=0)
with tempfile.TemporaryDirectory(prefix='good-company-demo-') as directory:
    c = Coordinator(Path(directory) / 'demo.sqlite')
    c.configure(json.loads((root / 'examples/profile.json').read_text())['profile'])
    c.ingest((root / 'examples/handbook.md').read_text(), 'examples/handbook.md',
             'Fictional club handbook', now.isoformat())
    snapshot = {'calendar': 'fictional-demo-only', 'complete': True,
                'window_start': now.isoformat(), 'window_end': (now + timedelta(days=30)).isoformat(),
                'checked_at': now.isoformat(), 'events': [{
                    'id': 'fictional-dinner-1', 'title': 'Community dinner',
                    'start': event_start.isoformat(), 'end': (event_start + timedelta(hours=2)).isoformat(),
                    'source': 'demo://community-dinner', 'location': 'Demo Hall, 123 Example Lane',
                    'rsvp': 'Reply to the event coordinator by Friday for a meal headcount.',
                    'attire': 'Comfortable clothes', 'status': 'confirmed'}]}
    c.import_calendar(snapshot, now=now)
    first = c.plan(now=now)
    second = c.plan(now=now)
    evidence = c.retrieve('When should I arrive to help?', now=now)
    queue = c.queue()
    print('GOOD COMPANY — FICTIONAL DEMO\n')
    print('Question: When should I arrive to help?')
    print('Retrieved evidence (the deployed OpenClaw agent turns this into a cited answer):')
    for item in evidence['evidence'][:1]:
        print(item['content'])
        print('Source:', item['source'], '—', item['section'])
    print('\nCalendar → reminder draft\n')
    print('Subject:', queue[0]['message']['subject'])
    print(queue[0]['message']['body'])
    print('\nStatus: DRAFT — no recipients, no approval, no email sent.')
    print(f'First planning pass: {len(first["created"])} reminders. Repeated pass: {len(second["created"])} new reminders.')
    print('Upcoming reminder times:', ', '.join(row['due'] for row in queue))
    print('\nCalendar changes: moving the dinner to a different hall.')
    snapshot['events'][0]['location'] = 'Demo Library community room'
    c.import_calendar(snapshot, now=now)
    print('Old reminder status:', c.reminder(queue[0]['id'])['status'])
    print('Replacement drafts:', len(c.plan(now=now)['created']))
