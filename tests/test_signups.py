from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from test_shifts import ShiftTests
from test_verified_replies import ReplyProvider
from test_core import NOW
from good_company.replies import VerifiedReply
from good_company.signups import apply
from good_company.tasks import WorkCoordinator
from good_company.providers import ProviderError


class SignupTests(ShiftTests):
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
