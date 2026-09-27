from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from test_shifts import ShiftTests
from test_verified_replies import ReplyProvider
from test_core import NOW
from test_tasks import volunteer
from good_company.replies import VerifiedReply
from good_company.replies import apply_verified_reply
from good_company.signups import apply
from good_company.tasks import WorkCoordinator
from good_company.providers import ProviderError


class SignupTests(ShiftTests):
    def confirmed_with_waitlist(self):
        self.prepare()
        for person in ['alex', 'sam']:
            apply(self.c, self.reply(person, 'signup', person), person, now=NOW)
        apply(self.c, self.reply('alex', 'accept_offer', 'accept'), 'accept', now=NOW)
        return self.c.db.execute("SELECT id FROM assignments WHERE status='assigned'").fetchone()[0]

    def test_normal_verified_decline_promotes_waitlist_without_confirming(self):
        assignment = self.confirmed_with_waitlist()
        provider = self.reply('alex', 'decline', 'normal-decline')
        provider.reply = replace(provider.reply, target_id=assignment)
        apply_verified_reply(self.c, provider, 'normal-decline', now=NOW)
        status = self.c.shift_status('packing')
        self.assertEqual(status['reserved_offers'], 1)
        self.assertEqual(status['filled'], 0)
        self.assertEqual(self.c.db.execute("SELECT volunteer_id FROM assignments WHERE status='offered'").fetchone()[0], 'sam')
        with self.assertRaises(ProviderError):
            apply_verified_reply(self.c, provider, 'normal-decline', now=NOW)

    def test_operator_decline_promotes_waitlist(self):
        assignment = self.confirmed_with_waitlist()
        self.c.decline_task(assignment, 'alex', 'verified fixture', now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)

    def test_decline_does_not_promote_someone_who_opted_out(self):
        assignment = self.confirmed_with_waitlist()
        person = volunteer('sam')
        person['accepts_delegation'] = False
        self.c.set_volunteer(person, 'participant opted out', now=NOW)
        self.c.decline_task(assignment, 'alex', 'verified fixture', now=NOW)
        status = self.c.shift_status('packing')
        self.assertEqual(status['reserved_offers'], 0)
        self.assertEqual(status['filled'], 0)

    def test_decline_leaves_another_shift_reservation_intact(self):
        assignment = self.confirmed_with_waitlist()
        shift = self.shift()
        shift.update(id='other', capacity=1, slots=shift['slots'][:1], signup_required=True)
        shift['slots'][0].update(start='2026-09-29T17:00:00-07:00', end='2026-09-29T17:30:00-07:00')
        self.c.add_shift(shift, 'different shift', now=NOW)
        for person in ['alex', 'sam']:
            message = 'other-' + person
            provider = self.reply(person, 'signup', message)
            provider.reply = replace(provider.reply, target_id='other:one')
            apply(self.c, provider, message, now=NOW)
        before = self.c.shift_status('other')
        self.c.decline_task(assignment, 'alex', 'verified fixture', now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)
        self.assertEqual(self.c.shift_status('other'), before)

    def test_paused_decline_releases_without_promoting(self):
        assignment = self.confirmed_with_waitlist()
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'owner paused', now=NOW)
        provider = self.reply('alex', 'decline', 'paused-decline')
        provider.reply = replace(provider.reply, target_id=assignment)
        apply_verified_reply(self.c, provider, 'paused-decline', now=NOW)
        status = self.c.shift_status('packing')
        self.assertEqual(status['reserved_offers'], 0)
        self.assertEqual(status['filled'], 0)

    def test_resume_promotes_waitlist_without_automatic_confirmation(self):
        assignment = self.confirmed_with_waitlist()
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'owner paused', now=NOW)
        self.c.decline_task(assignment, 'alex', 'verified fixture', now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'], [])
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)
        policy['enabled'] = True
        self.c.configure_autonomy(policy, 'owner resumed', now=NOW)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'], [])
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        self.c.delegate(now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)
        notices = self.c.task_queue()
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['kind'], 'offer')
        self.assertEqual(notices[0]['message']['to'], ['sam@example.invalid'])

    def test_resume_does_not_offer_to_waitlisted_person_who_opted_out(self):
        assignment = self.confirmed_with_waitlist()
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'owner paused', now=NOW)
        self.c.decline_task(assignment, 'alex', 'verified fixture', now=NOW)
        self.c.set_contact_consent('sam@example.invalid', False, 'verified stop', now=NOW)
        policy['enabled'] = True
        self.c.configure_autonomy(policy, 'owner resumed', now=NOW)
        self.c.delegate(now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)

    def test_concurrent_resume_cycles_reserve_only_one_waitlist_offer(self):
        assignment = self.confirmed_with_waitlist()
        policy = self.c.autonomy()
        policy['enabled'] = False
        self.c.configure_autonomy(policy, 'owner paused', now=NOW)
        self.c.decline_task(assignment, 'alex', 'verified fixture', now=NOW)
        policy['enabled'] = True
        self.c.configure_autonomy(policy, 'owner resumed', now=NOW)
        path = Path(self.tmp.name) / 'tasks.sqlite'
        def resume(_):
            c = WorkCoordinator(path)
            try:
                return c.delegate(now=NOW)
            finally:
                c.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(resume, range(2)))
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 1)
        self.assertEqual(self.c.shift_status('packing')['filled'], 0)
        self.assertEqual(self.c.db.execute("SELECT count(*) FROM audit WHERE action='shift_offer_reserved'").fetchone()[0], 2)

    def reply(self,sender,action,message):
        p=ReplyProvider();p.reply=VerifiedReply(message,sender+'@example.invalid',True,'verified-fixture',action,'packing:one');return p

    def prepare(self):
        self.c.close_task('chairs','cancelled','fixture',now=NOW)
        shift=self.shift();shift.update(capacity=1,slots=shift['slots'][:1],signup_required=True)
        self.c.add_shift(shift,'fixture',now=NOW)

    def test_simultaneous_signups_reserve_one_and_waitlist_one(self):
        self.prepare();path=Path(self.tmp.name)/'tasks.sqlite'
        def signup(person):
            c=WorkCoordinator(path)
            try:return apply(c,self.reply(person,'signup',person),person,now=NOW)['status']
            finally:c.db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:states=list(pool.map(signup,['alex','sam']))
        self.assertEqual(sorted(states),['offered','waitlisted'])
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'],1)
        self.assertEqual(self.c.shift_status('packing')['filled'],0)
        self.assertEqual(self.c.delegate(now=NOW)['assigned'],[])

    def test_decline_reserves_qualified_replacement_and_rsvp_is_separate(self):
        self.prepare()
        for person in ['alex','sam']:apply(self.c,self.reply(person,'signup',person),person,now=NOW)
        apply(self.c,self.reply('alex','decline_offer','decline'),'decline',now=NOW)
        self.assertEqual(self.c.shift_status('packing')['filled'],0)
        apply(self.c,self.reply('sam','accept_offer','accept'),'accept',now=NOW)
        self.assertEqual(self.c.shift_status('packing')['filled'],1)
        with self.assertRaises(ProviderError):apply(self.c,self.reply('sam','accept_offer','accept'),'accept',now=NOW)
        p=self.reply('alex','signup','spoof');p.reply=replace(p.reply,authenticated=False)
        with self.assertRaises(ProviderError):apply(self.c,p,'spoof',now=NOW)

    def test_cancelled_slot_releases_reported_offer_capacity(self):
        self.prepare()
        apply(self.c,self.reply('alex','signup','signup'),'signup',now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'],1)
        self.c.close_task('packing:one','cancelled','owner cancelled fixture',now=NOW)
        status=self.c.shift_status('packing')
        self.assertEqual(status['reserved_offers'],0)
        self.assertEqual(status['filled'],0)
        self.assertEqual(status['unfilled'],0)
        self.assertFalse(status['slots'][0]['reserved_offer'])

    def test_wrong_mailbox_or_paused_scope_never_reads_reply(self):
        self.prepare()
        for paused in (False, True):
            with self.subTest(paused=paused):
                provider = self.reply('alex', 'signup', 'must-not-fetch')
                account = provider.account()
                if paused:
                    policy = self.c.autonomy()
                    policy['enabled'] = False
                    self.c.configure_autonomy(policy, 'owner paused', now=NOW)
                else:
                    account = replace(account, sender='unrelated@example.invalid')
                provider.account = lambda: account
                provider.verified_reply = lambda message: self.fail('Out-of-scope message was fetched')
                before = self.c.shift_status('packing')
                with self.assertRaisesRegex(ProviderError, 'signup_account_outside_remit'):
                    apply(self.c, provider, 'must-not-fetch', now=NOW)
                self.assertEqual(self.c.shift_status('packing'), before)

    def test_mailbox_changed_during_read_does_not_apply_signup(self):
        self.prepare()
        provider = self.reply('alex', 'signup', 'changed-scope')
        reply = provider.reply
        def read(message):
            policy = self.c.autonomy()
            policy['sender'] = 'new-owner@example.invalid'
            self.c.configure_autonomy(policy, 'owner changed mailbox', now=NOW)
            return reply
        provider.verified_reply = read
        with self.assertRaisesRegex(ProviderError, 'signup_account_outside_remit'):
            apply(self.c, provider, 'changed-scope', now=NOW)
        self.assertEqual(self.c.shift_status('packing')['reserved_offers'], 0)
