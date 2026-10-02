"""A complete fictional shift lifecycle over the isolated HTTP mailbox."""
import unittest
import urllib.error

from loopback_mail_lab import MailLab
from good_company.intake import dispatch
from good_company.providers import Delivery, ProviderError
from test_core import NOW
import test_shifts as shift_base
import test_signups as signup_base
import test_tasks as task_base

OBSERVED = {}


class FoodBankLabTests(unittest.TestCase):
    setUp = shift_base.ShiftTests.setUp
    tearDown = shift_base.ShiftTests.tearDown
    prepare = signup_base.SignupTests.prepare
    shift = shift_base.ShiftTests.shift

    def test_eligible_signup_verified_decline_and_qualified_replacement(self):
        self.prepare()
        # Two ineligible people are authorized to reply but cannot reserve this shift.
        policy = self.c.autonomy()
        policy['allowed_recipients'] += ['lee@example.invalid', 'pat@example.invalid']
        self.c.configure_autonomy(policy, 'Fictional local pilot', now=NOW)
        lee = task_base.volunteer('lee'); lee['roles'] = ['guest']
        pat = task_base.volunteer('pat'); pat['accepts_delegation'] = False
        self.c.set_volunteer(lee, 'Fictional role', now=NOW)
        self.c.set_volunteer(pat, 'Fictional opt-out', now=NOW)
        with MailLab(self.tmp.name) as lab:
            p = lab.provider()
            for person in ('lee', 'pat'):
                mid = lab.submit(person, 'SIGNUP packing:one')
                with self.assertRaises(ProviderError):
                    dispatch(self.c, p, mid, now=NOW)
            self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)
            for person, expected in [('alex', 'offered'), ('sam', 'waitlisted')]:
                mid = lab.submit(person, 'SIGNUP packing:one')
                self.assertEqual(dispatch(self.c, p, mid, now=NOW)['status'], expected)
            self.c.delegate(now=NOW)
            notice = next(n for n in self.c.task_queue() if n['kind'] == 'offer' and n['status'] == 'pending')
            delivery = Delivery(self.c, p)
            delivery.send('task', notice['id'], now=NOW)
            self.assertEqual(self.c.shift_status('packing')['filled'], 0)
            with self.assertRaises(ValueError):
                delivery.send('task', notice['id'], now=NOW)
            accepted = lab.accepted()
            self.assertEqual(len(accepted), 1)
            self.assertEqual(accepted[0]['recipients'], ['alex@example.invalid'])
            forged = lab.submit('pat', 'DECLINE-OFFER packing:one', claimed_sender='alex@example.invalid')
            with self.assertRaises(ProviderError):
                dispatch(self.c, p, forged, now=NOW)
            self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)
            mid = lab.submit('alex', 'DECLINE-OFFER packing:one')
            self.assertEqual(dispatch(self.c, p, mid, now=NOW)['status'], 'declined')
            with self.assertRaises(ProviderError):
                dispatch(self.c, p, mid, now=NOW)
            self.c.delegate(now=NOW)
            replacement = next(n for n in self.c.task_queue() if n['kind'] == 'offer' and n['status'] == 'pending')
            self.assertEqual(replacement['message']['to'], ['sam@example.invalid'])
            delivery.send('task', replacement['id'], now=NOW)
            self.assertEqual(self.c.shift_status('packing')['filled'], 0)
            mid = lab.submit('sam', 'ACCEPT packing:one')
            self.assertEqual(dispatch(self.c, p, mid, now=NOW)['status'], 'confirmed')
            self.assertEqual(self.c.shift_status('packing')['filled'], 1)
            self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)
            self.assertEqual(len(lab.accepted()), 2)
            stored = '\n'.join(self.c.db.iterdump())
            self.assertNotIn('Lab credential transport', stored)
            OBSERVED['lifecycle'] = {'accepted_local_notices': 2, 'confirmed_capacity': 1,
                'ineligible_signups_rejected': 2, 'spoof_rejected': True, 'replay_rejected': True}

    def test_lab_enforces_credentials_and_rejects_real_recipients(self):
        with MailLab(self.tmp.name) as lab:
            with self.assertRaises(urllib.error.HTTPError):
                lab.request('/submit', {'command': 'STOP', 'sender': 'alex@example.invalid'}, token='wrong')
            with self.assertRaises(urllib.error.HTTPError):
                lab.request('/send', {'message': {'sender': lab.owner, 'to': ['person@example.com'], 'bcc': []},
                                     'operation': 'one', 'key': 'one'})
            self.assertEqual(lab.accepted(), [])

    def test_lab_receipt_is_idempotent_and_reconcilable(self):
        with MailLab(self.tmp.name) as lab:
            p = lab.provider()
            message = {'sender': lab.owner, 'to': ['alex@example.invalid'], 'bcc': [], 'body': 'Fictional offer'}
            first = p.send(message, 'task:one', 'task:one')
            self.assertEqual(p.send(message, 'task:one', 'task:one'), first)
            self.assertEqual(p.reconcile('task:one'), first)
            with self.assertRaises(ProviderError):
                p.send(dict(message, body='Changed'), 'task:one', 'task:one')
            self.assertEqual(len(lab.accepted()), 1)
