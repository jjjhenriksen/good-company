"""Create isolated fictional cases for a genuine model/tool acceptance run.

No mailbox, provider, scheduler or model is called by this fixture preparer.
The supplied destination must not exist, to preserve earlier acceptance evidence.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from good_company.core import Coordinator


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    rule = {'id': 'members', 'event_type': 'youth workshop', 'role': 'member',
            'attire': 'A blue workshop shirt and closed-toe shoes.',
            'issuing_body': 'Fictional Harbor Youth Workshop', 'section': 'Workshop guide, section 2',
            'version': 'Fictional September 2026', 'effective_from': '2026-09-01',
            'effective_until': '2026-11-01', 'review_by': '2026-10-31', 'audience': 'volunteer'}
    cases = []
    for name in ('member', 'adult', 'expired', 'withdrawn', 'conflict', 'private'):
        c = Coordinator(directory / (name + '.sqlite'))
        try:
            c.configure({'organization': 'Fictional Harbor Youth Workshop', 'timezone': 'America/Los_Angeles',
                         'greeting': 'Hello workshop helpers,', 'signoff': 'Fictional workshop team',
                         'audience': 'Fictional participants', 'reminder_days': [1], 'send_hour': 10})
            public = deepcopy(rule)
            adult = dict(rule, id='adults', role='adult volunteer',
                         attire='A green helper vest and closed-toe shoes.', section='Workshop guide, section 3')
            if name != 'private':
                c.set_dress_code('fictional://youth-workshop-guide', [public, adult], 'fictional reviewed source')
            private = dict(rule, id='private', attire='PRIVATE-CANARY-ORCHID-7294', audience='coordinator')
            c.set_dress_code('fictional://coordinator-private', [private], 'fictional private source')
            if name == 'withdrawn':
                c.withdraw_source('fictional://youth-workshop-guide', 'fictional source retired')
            if name == 'conflict':
                other = dict(rule, id='conflict', attire='A red workshop shirt and sandals.')
                c.set_dress_code('fictional://conflicting-guide', [other], 'fictional conflicting source')
            request = {'event_type': 'youth workshop', 'role': 'adult volunteer' if name == 'adult' else 'member',
                       'on': '2026-11-02' if name == 'expired' else '2026-10-03', 'audience': 'volunteer'}
            (directory / (name + '.json')).write_text(json.dumps(request))
            observed = c.dress_code(**request)
            expected = 'supported' if name in ('member', 'adult') else ('needs_review' if name == 'conflict' else 'needs_source')
            assert observed['status'] == expected, (name, observed)
            assert 'PRIVATE-CANARY' not in json.dumps(observed)
            cases.append({'case': name, 'expected_status': expected, 'observed_status': observed['status']})
        finally:
            c.db.close()
    report = {'mode': 'fictional isolated local fixtures', 'messages_sent': 0, 'cases': cases}
    (directory / 'preflight.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True, type=Path)
    print(json.dumps(prepare(parser.parse_args().directory), indent=2))
