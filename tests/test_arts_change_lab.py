"""Rehearsal cancellation, team boundaries and corrections through the HTTP lab."""
import copy
from pathlib import Path
import unittest

from loopback_mail_lab import MailLab
from good_company.core import digest
from good_company.corrections import CorrectionCoordinator
from good_company.providers import Delivery
from test_core import NOW, DUE, snapshot
import test_tasks as base

OBSERVED = {}


class ArtsChangeLabTests(unittest.TestCase):
    def setUp(self):
        base.TaskTests.setUp(self)
        self.c.db.close()
        self.c = CorrectionCoordinator(Path(self.tmp.name) / 'tasks.sqlite')
        self.c.close_task('chairs', 'cancelled', 'Fictional setup', now=NOW)
        policy = self.c.autonomy()
        policy.update(program_audiences={'arts': ['alex@example.invalid'], 'food': ['sam@example.invalid']},
                      max_reminders_per_day=8)
        self.c.configure_autonomy(policy, 'Fictional program remit', now=NOW)
        for person, role in [('alex', 'arts crew'), ('sam', 'food crew')]:
            v = base.volunteer(person); v['roles'].append(role)
            self.c.set_volunteer(v, 'Fictional team roster', now=NOW)
        self.data = snapshot()
        first = self.data['events'][0]
        first.pop('rsvp', None)
        first.update(id='rehearsal-one', title='Fictional rehearsal', program='arts',
                     event_type='service activity', dress_applicability='not_applicable')
        self.data['events'].append(dict(first, id='packing-event', title='Fictional packing event', program='food'))
        self.c.import_calendar(self.data, now=NOW)
        self.events = {e['payload']['program']: e['id'] for e in self.c.events()}
        for program, role in [('arts', 'arts crew'), ('food', 'food crew')]:
            task = base.task(program + '-setup')
            task.update(event_id=self.events[program], eligible_roles=[role])
            self.c.add_task(task, 'Fictional event-linked setup', now=NOW)
        self.c.delegate(now=NOW)

    tearDown = base.TaskTests.tearDown

    def send_originals(self, lab):
        delivery = Delivery(self.c, lab.provider())
        tasks = [n for n in self.c.task_queue() if n['kind'] == 'assignment']
        for task in tasks:
            delivery.send('task', task['id'], now=NOW)
        ids = self.c.plan(now=NOW)['automatically_authorized']
        self.data['checked_at'] = DUE
        self.c.import_calendar(self.data, now=DUE)
        original = {}
        for rid in ids:
            item = self.c.reminder(rid)
            program = next(p for p, eid in self.events.items() if eid == item['event_id'])
            self.assertEqual(item['message']['bcc'], ['alex@example.invalid'] if program == 'arts' else ['sam@example.invalid'])
            delivery.send('event', rid, now=DUE)
            original[program] = self.c.reminder(rid)
        return delivery, original, tasks

    def test_cancellation_preserves_team_receipts_and_cancels_linked_work(self):
        with MailLab(self.tmp.name) as lab:
            delivery, original, tasks = self.send_originals(lab)
            before = copy.deepcopy(original)
            self.data['events'] = [e for e in self.data['events'] if e['program'] == 'food']
            changes = self.c.import_calendar(self.data, now=DUE)
            impact = next(i for i in changes['impacts'] if i['task_id'] == 'arts-setup')
            self.assertEqual(impact['reason'], 'event_cancelled')
            self.assertTrue(impact['attempts'][0]['receipt'].startswith('loopback-lab:'))
            arts_task = next(n for n in tasks if n['message']['to'] == ['alex@example.invalid'])
            for queued in self.c.task_queue():
                if queued['assignment_id'] == arts_task['assignment_id'] and queued['id'] != arts_task['id']:
                    self.assertEqual(queued['status'], 'cancelled')
                    with self.assertRaises(ValueError):
                        delivery.send('task', queued['id'], now=DUE)
            for kind, old in [('event', original['arts']), ('task', arts_task)]:
                message = {key: old['message'][key] for key in ('sender', 'to', 'bcc')}
                message.update(subject='Fictional rehearsal cancelled', body='Rehearsal and its linked setup are cancelled.')
                correction = self.c.create_correction(kind, old['id'], message, digest(message),
                                                     'Fictional authoritative cancellation', now=DUE)['id']
                self.assertEqual(self.c.create_correction(kind, old['id'], message, digest(message),
                                 'Fictional authoritative cancellation', now=DUE)['id'], correction)
                delivery.send('correction', correction, now=DUE)
                with self.assertRaises(ValueError):
                    delivery.send('correction', correction, now=DUE)
            for program in ('arts', 'food'):
                self.assertEqual(self.c.reminder(original[program]['id'])['receipt'], before[program]['receipt'])
            self.assertEqual(self.c.db.execute("SELECT status FROM tasks WHERE id='food-setup'").fetchone()[0], 'open')
            accepted = lab.accepted()
            self.assertEqual(len(accepted), 6)
            corrections = [r for r in accepted if r['operation'].startswith('correction:')]
            self.assertTrue(all(r['recipients'] == ['alex@example.invalid'] for r in corrections))
            self.assertEqual(len(corrections), 2)
            OBSERVED['cancellation'] = {'accepted_local_notices': 6, 'corrections': 2,
                'cross_team_corrections': 0, 'original_receipts_preserved': True,
                'linked_follow_up_cancelled': True, 'duplicate_attempts_rejected': True}

    def test_a_correction_cannot_expand_to_another_program(self):
        with MailLab(self.tmp.name) as lab:
            _, original, _ = self.send_originals(lab)
            self.data['events'][0]['location'] = 'Fictional replacement venue'
            self.c.import_calendar(self.data, now=DUE)
            message = {key: original['arts']['message'][key] for key in ('sender', 'to', 'bcc')}
            message.update(subject='Rehearsal moved', body='Use the replacement venue.', bcc=['sam@example.invalid'])
            with self.assertRaises(ValueError):
                self.c.create_correction('event', original['arts']['id'], message, digest(message),
                                         'Fictional move authority', now=DUE)
            self.assertEqual(self.c.correction_queue(), [])
            self.assertEqual(len(lab.accepted()), 4)
