import unittest
import test_core as base
from test_core import NOW, DUE, snapshot
from good_company.core import digest


class EventHistoryTests(unittest.TestCase):
    setUp = base.CoordinationTests.setUp
    tearDown = base.CoordinationTests.tearDown
    draft = base.CoordinationTests.draft
    approved = base.CoordinationTests.approved

    def changed_after_attempt(self, outcome):
        rid = self.approved()
        self.c.import_calendar(snapshot(DUE), now=DUE)
        self.c.claim(rid, now=DUE)
        self.c.receipt(rid, outcome, 'fictional provider reference', now=DUE)
        changed = snapshot(DUE); changed['events'][0]['location']='Updated venue'
        self.c.import_calendar(changed, now=DUE)
        planned = self.c.plan(now=DUE)
        self.assertEqual(planned['created'], [])
        self.assertEqual(planned['exceptions'][0]['previous_reminder_id'], rid)
        self.assertEqual(self.c.reminder(rid)['status'], outcome)

    def test_sent_revision_is_not_resent_after_change(self):
        self.changed_after_attempt('sent')

    def test_uncertain_revision_is_not_retried_after_change(self):
        self.changed_after_attempt('uncertain')

    def test_failed_attempt_needs_explicit_reconciliation(self):
        self.changed_after_attempt('failed')

    def test_claim_blocks_legacy_replacement_created_before_upgrade(self):
        old = self.approved()
        changed = snapshot(DUE); changed['events'][0]['location']='Updated venue'
        self.c.import_calendar(changed, now=DUE)
        rid = self.c.plan(now=DUE)['created'][0]
        message=self.c.reminder(rid)['message'];message['to']=['demo@example.invalid']
        self.c.edit(rid,message,now=DUE);self.c.approve(rid,digest(message),'owner',now=DUE)
        # Legacy fixture: old version had sent a prior revision before this queue record.
        with self.c.db:
            self.c.db.execute("UPDATE reminders SET status='sent',claimed_at=? WHERE id=?", (DUE,old))
        with self.assertRaisesRegex(ValueError, 'previous revision'):
            self.c.claim(rid,now=DUE)

    def test_new_empty_scope_remembers_sync_watermark(self):
        current=snapshot(DUE);current['calendar']='new-scope';current['events']=[]
        self.c.import_calendar(current,now=DUE)
        older=snapshot();older['calendar']='new-scope'
        with self.assertRaisesRegex(ValueError,'older'):
            self.c.import_calendar(older,now=DUE)
        self.assertFalse(any(e['calendar']=='new-scope' for e in self.c.events()))

    def test_later_distinct_cadence_still_sends(self):
        data=snapshot(DUE)
        data['events'][0].update(start='2026-10-03T17:30:00-07:00',end='2026-10-03T19:00:00-07:00')
        self.c.import_calendar(data,now=DUE);self.c.plan(now=DUE)
        active=[r for r in self.c.queue() if r['status']=='draft']
        for row in active:
            msg=row['message'];msg['to']=['demo@example.invalid']
            self.c.edit(row['id'],msg,now=DUE);self.c.approve(row['id'],digest(msg),'owner',now=DUE)
        first=next(r for r in active if r['kind']=='7d')
        self.c.claim(first['id'],now=DUE);self.c.receipt(first['id'],'sent','fixture',now=DUE)
        later='2026-10-02T16:00:00Z';data['checked_at']=later
        self.c.import_calendar(data,now=later)
        last=next(r for r in active if r['kind']=='1d')
        self.assertEqual(self.c.claim(last['id'],now=later)['id'],last['id'])
