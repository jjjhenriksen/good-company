#!/usr/bin/env python3
"""Deterministic replay with fictional data and a simulated clock; no network."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from good_company.tasks import WorkCoordinator
root=Path(__file__).resolve().parents[1]
def read(name): return json.loads((root/'examples'/name).read_text())
now='2026-09-25T16:00:00Z'
with tempfile.TemporaryDirectory(prefix='good-company-autonomy-') as directory:
    c=WorkCoordinator(Path(directory)/'demo.sqlite')
    c.configure(read('profile.json')['profile'])
    c.configure_autonomy(**read('autonomy.json'),now=now)
    c.set_dress_code(**read('dress-code.json'),now=now)
    print('GOOD COMPANY — FICTIONAL AUTONOMY REPLAY\nSimulated date: September 25, 2026. No network or live email.\n')
    result=c.dress_code(event_type='service activity',role='member',on='2026-09-27',now=now)
    print('What do I wear?')
    print(result['attire'])
    print('Source:',result['citations'][0]['source'],result['citations'][0]['section'])
    snapshot={'calendar':'demo-events-only','complete':True,'checked_at':now,
              'window_start':'2026-09-25T00:00:00Z','window_end':'2026-10-01T00:00:00Z',
              'events':[{'id':'demo-service','title':'Service activity','event_type':'service activity',
                         'dress_code_role':'member','start':'2026-09-27T17:30:00-07:00',
                         'end':'2026-09-27T19:00:00-07:00','location':'Demo community hall',
                         'source':'demo://calendar/service','status':'confirmed'}]}
    c.import_calendar(snapshot,now=now)
    planned=c.plan(now=now)
    print('\nRoutine reminders authorized without per-message review:',len(planned['automatically_authorized']))
    for v in read('team.json'): c.set_volunteer(**v,now=now)
    for t in read('tasks.json'): c.add_task(**t,now=now)
    allocated=c.delegate(now=now)
    print('\nTask assignments:')
    for assignment in allocated['assigned']:
        print(assignment['task_id'],'→',assignment['volunteer_id'],'(notice queued, not sent)')
    print('Second allocation pass:',len(c.delegate(now=now)['assigned']),'new assignments')
    first=next(a for a in allocated['assigned'] if a['volunteer_id']=='alex')
    c.decline_task(first['assignment_id'],'alex','Fictional verified decline',now=now)
    reassigned=c.delegate(now=now)
    print('After a decline:',[(a['task_id'],a['volunteer_id']) for a in reassigned['assigned']])
    print('\nAll notices remain local queue records. No provider receipt has been fabricated.')
