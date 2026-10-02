"""Verified STOP across queued event/task workflows with one shared budget."""
from pathlib import Path
import unittest

from loopback_mail_lab import MailLab
from good_company.intake import dispatch
from good_company.providers import Delivery, ProviderError
from good_company.tasks import WorkCoordinator
from test_core import NOW, DUE, snapshot
import test_tasks as base

OBSERVED = {}


class MutualAidLabTests(unittest.TestCase):
    def setUp(self):
        base.TaskTests.setUp(self)
        policy = self.c.autonomy()
        policy['max_reminders_per_day'] = 2
        self.c.configure_autonomy(policy, 'Fictional shared communication budget', now=NOW)
        self.c.add_task(base.task('other-helper'), 'Fictional second helper task', now=NOW)
        self.c.delegate(now=NOW)
        self.data = snapshot()
        self.data['events'][0].update(title='Fictional mutual aid briefing',
                                    event_type='service activity', dress_applicability='not_applicable')
        self.c.import_calendar(self.data, now=NOW)
        self.original_event = self.c.plan(now=NOW)['automatically_authorized'][0]

    tearDown = base.TaskTests.tearDown

    def test_stop_blocks_both_workflows_while_unaffected_work_uses_shared_budget(self):
        with MailLab(self.tmp.name) as lab:
            p = lab.provider()
            forged = lab.submit('pat', 'STOP', claimed_sender='alex@example.invalid')
            with self.assertRaises(ProviderError):
                dispatch(self.c, p, forged, now=NOW)
            self.assertTrue(self.c.contact_allowed('alex@example.invalid'))
            mid = lab.submit('alex', 'STOP')
            self.assertEqual(dispatch(self.c, p, mid, now=NOW)['status'], 'applied')
            with self.assertRaises(ProviderError):
                dispatch(self.c, p, mid, now=NOW)
            self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
            delivery = Delivery(self.c, p)
            self.data['checked_at'] = DUE
            self.c.import_calendar(self.data, now=DUE)
            with self.assertRaises(ValueError):
                delivery.send('event', self.original_event, now=DUE)
            for notice in self.c.task_queue():
                if notice['message']['to'] == ['alex@example.invalid']:
                    self.assertEqual(notice['status'], 'cancelled')
                    with self.assertRaises(ValueError):
                        delivery.send('task', notice['id'], now=DUE)
            fresh = self.c.plan(now=DUE)['automatically_authorized'][0]
            self.assertEqual(self.c.reminder(fresh)['message']['bcc'], ['sam@example.invalid'])
            delivery.send('event', fresh, now=DUE)
            task = next(n for n in self.c.task_queue() if n['kind'] == 'assignment'
                        and n['message']['to'] == ['sam@example.invalid'])
            delivery.send('task', task['id'], now=DUE)
            extra = base.task('extra-help')
            extra.update(start='2026-09-26T19:00:00Z', end='2026-09-26T19:30:00Z')
            self.c.add_task(extra, 'Fictional additional task', now=DUE)
            self.c.delegate(now=DUE)
            third = next(n for n in self.c.task_queue() if n['kind'] == 'assignment' and n['status'] == 'pending')
            self.c.db.close()
            self.c = WorkCoordinator(Path(self.tmp.name) / 'tasks.sqlite')
            delivery = Delivery(self.c, p)
            with self.assertRaisesRegex(ValueError, 'shared daily'):
                delivery.send('task', third['id'], now=DUE)
            self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
            self.assertEqual(self.c.communication_budget(now=DUE)['used'], 2)
            accepted = lab.accepted()
            self.assertEqual(len(accepted), 2)
            self.assertTrue(all(r['recipients'] == ['sam@example.invalid'] for r in accepted))
            OBSERVED['stop'] = {'accepted_local_notices': 2, 'stopped_helper_notices': 0,
                'event_and_task_budget_used': 2, 'third_notice_blocked': True,
                'consent_and_budget_survive_restart': True, 'spoof_and_replay_rejected': True}

    def test_paused_sending_still_processes_credential_bound_stop(self):
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'Fictional owner pause', now=NOW)
        with MailLab(self.tmp.name) as lab:
            mid = lab.submit('alex', 'STOP')
            self.assertEqual(dispatch(self.c, lab.provider(), mid, now=NOW)['status'], 'applied')
            self.assertFalse(self.c.contact_allowed('alex@example.invalid'))
            task = next(n for n in self.c.task_queue() if n['message']['to'] == ['sam@example.invalid'])
            with self.assertRaises(ValueError):
                Delivery(self.c, lab.provider()).send('task', task['id'], now=NOW)
            self.assertEqual(lab.accepted(), [])
