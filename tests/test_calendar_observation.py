"""An absent provider timestamp must never become current observation evidence."""
from dataclasses import replace
import json
from pathlib import Path
import unittest

import test_core as core
from test_core import snapshot
from test_providers import FixtureProvider
from good_company.providers import ProviderError, import_complete_calendar


class CalendarObservationTests(unittest.TestCase):
    setUp = core.CoordinationTests.setUp
    tearDown = core.CoordinationTests.tearDown

    def test_undated_snapshot_preserves_events_approvals_and_watermark(self):
        rid = core.CoordinationTests.approved(self)
        before = self.c.events(), self.c.reminder(rid), list(self.c.db.execute('SELECT * FROM calendar_sync'))
        for absent in (None, '', False, 0, ' ', '2026-09-27T10:00:00'):
            with self.subTest(checked_at=absent):
                data = snapshot(absent)
                data['events'] = []
                with self.assertRaises(ValueError):
                    self.c.import_calendar(data)
                self.assertEqual((self.c.events(), self.c.reminder(rid), list(self.c.db.execute('SELECT * FROM calendar_sync'))), before)

    def test_undated_provider_page_preserves_calendar(self):
        policy = json.loads(Path('examples/autonomy.json').read_text())['policy']
        self.c.configure_autonomy(policy, 'fictional owner')
        before = self.c.events()
        data = snapshot()
        for absent in (None, '', False, 0, ' ', '2026-09-27T10:00:00'):
            with self.subTest(checked_at=absent):
                p = FixtureProvider()
                p.pages = [replace(p.pages[0], checked_at=absent, events=[])]
                with self.assertRaises(ProviderError):
                    import_complete_calendar(self.c, p, data['calendar'], data['window_start'], data['window_end'])
                self.assertEqual(self.c.events(), before)

    def test_undated_later_page_never_applies_partial_snapshot(self):
        policy = json.loads(Path('examples/autonomy.json').read_text())['policy']
        self.c.configure_autonomy(policy, 'fictional owner')
        p = FixtureProvider()
        p.pages = [replace(p.pages[0], events=[], next_cursor='1'),
                   replace(p.pages[0], checked_at=None, events=[])]
        before = self.c.events()
        data = snapshot()
        with self.assertRaises(ProviderError):
            import_complete_calendar(self.c, p, data['calendar'], data['window_start'], data['window_end'])
        self.assertEqual(self.c.events(), before)

    def test_explicit_observation_is_preserved_without_test_clock(self):
        policy = json.loads(Path('examples/autonomy.json').read_text())['policy']
        self.c.configure_autonomy(policy, 'fictional owner')
        p = FixtureProvider()
        data = snapshot()
        import_complete_calendar(self.c, p, data['calendar'], data['window_start'], data['window_end'])
        self.assertEqual(self.c.events()[0]['checked_at'], core.NOW)
        self.assertEqual(self.c.db.execute('SELECT checked_at FROM calendar_sync').fetchone()[0], core.NOW)

    draft = core.CoordinationTests.draft
