from dataclasses import replace
import unittest
import test_tasks as base
from test_core import NOW, snapshot
from good_company.providers import Account, CalendarPage, SendResult, ProviderError, Delivery, import_complete_calendar


class FixtureProvider:
    def __init__(self):
        self.identity = Account('fixture', 'fictional-account', 'coordinator@example.invalid', True,
                                frozenset({'demo-events-only'}), True, True, False, True)
        self.sent = []
        self.result = SendResult('accepted', 'fixture-receipt')
        self.pages = [CalendarPage('demo-events-only', snapshot()['events'], NOW, True, True)]
    def account(self):
        return self.identity
    def calendar_page(self, scope, start, end, cursor):
        return self.pages[int(cursor or 0)]
    def send(self, message, operation_id, idempotency_key):
        self.sent.append((message, operation_id, idempotency_key))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result
    def reconcile(self, operation_id):
        return self.result


class ProviderTests(unittest.TestCase):
    setUp = base.TaskTests.setUp
    tearDown = base.TaskTests.tearDown

    def test_permission_denial_never_claims(self):
        self.c.delegate(now=NOW)
        p = FixtureProvider()
        p.identity = replace(p.identity, unattended_send=False)
        n = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        with self.assertRaises(ProviderError):
            Delivery(self.c, p).send('task', n['id'], now=NOW)
        self.assertEqual(p.sent, [])
        self.assertEqual(next(x for x in self.c.task_queue() if x['id'] == n['id'])['status'], 'pending')

    def test_timeout_is_uncertain_and_reconciles_without_resend(self):
        self.c.delegate(now=NOW)
        p = FixtureProvider()
        p.result = TimeoutError('sensitive-provider-body')
        n = next(n for n in self.c.task_queue() if n['kind'] == 'assignment')
        delivery = Delivery(self.c, p)
        self.assertEqual(delivery.send('task', n['id'], now=NOW)['status'], 'uncertain')
        with self.assertRaises(ValueError):
            delivery.send('task', n['id'], now=NOW)
        p.result = SendResult('accepted', 'fixture-lookup-receipt')
        self.assertEqual(delivery.reconcile('task', n['id'], now=NOW)['status'], 'sent')
        self.assertEqual(len(p.sent), 1)
        self.assertIsNone(p.sent[0][2])

    def test_incomplete_page_preserves_existing_calendar(self):
        p = FixtureProvider()
        data = snapshot()
        self.c.import_calendar(data, now=NOW)
        p.pages = [replace(p.pages[0], events=[], complete_page=False)]
        with self.assertRaises(ProviderError):
            import_complete_calendar(self.c, p, data['calendar'], data['window_start'], data['window_end'], now=NOW)
        self.assertFalse(self.c.events()[0]['cancelled'])

    def test_complete_pagination_and_duplicate_occurrence_rejection(self):
        p = FixtureProvider()
        data = snapshot()
        p.pages = [replace(p.pages[0], next_cursor='1'), replace(p.pages[0], events=[])]
        result = import_complete_calendar(self.c, p, data['calendar'], data['window_start'], data['window_end'], now=NOW)
        self.assertEqual(result['imported'], 1)
        p.pages[1] = replace(p.pages[0], next_cursor=None)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            import_complete_calendar(self.c, p, data['calendar'], data['window_start'], data['window_end'], now=NOW)
