from dataclasses import replace
import json
from pathlib import Path
import unittest

import test_tasks as fixtures
from test_core import NOW
from test_verified_replies import ReplyProvider
from good_company.providers import ProviderError
from good_company.replies import VerifiedReply, apply_verified_reply
from good_company.tasks import WorkCoordinator


class AccessibleAcceptanceTests(unittest.TestCase):
    setUp = fixtures.TaskTests.setUp
    tearDown = fixtures.TaskTests.tearDown

    def preferences(self, language='es', format='structured_plain_text'):
        return {'timezone': 'Europe/Madrid' if language == 'es' else 'America/Los_Angeles',
                'channels': ['email'], 'quiet_start': 21, 'quiet_end': 7,
                'min_interval_hours': 2, 'language': language, 'format': format}

    def source(self):
        text = 'Performers arrive at 18:00 on 27 September. Guests arrive at 18:30. If rehearsal is cancelled, do not travel.'
        source = 'https://fictional.example.invalid/rehearsal-guide'
        self.c.ingest(text, source, 'Rehearsal guide', NOW)
        item = self.c.retrieve('Performers', now=NOW)['evidence'][0]
        self.c.register_translation(source=source, section=item['section'], original=text,
            translated='Los artistas llegan a las 18:00 el 27 de septiembre. Los invitados llegan a las 18:30. Si se cancela el ensayo, no viajes.',
            language='es', authority='fixture bilingual reviewer', now=NOW)
        return source, text

    def test_verified_preferences_persist_and_spoof_cannot_change_them(self):
        p = ReplyProvider()
        p.reply = VerifiedReply('preferences-one', 'alex@example.invalid', True,
            'fixture provider identity', 'preferences', preferences=self.preferences())
        apply_verified_reply(self.c, p, 'preferences-one', now=NOW)
        self.c.db.close()
        self.c = WorkCoordinator(Path(self.tmp.name) / 'tasks.sqlite')
        saved = self.c.db.execute('SELECT payload FROM contact_preferences WHERE address=?', ('alex@example.invalid',)).fetchone()[0]
        self.assertEqual(json.loads(saved), self.preferences())
        p.reply = replace(p.reply, message_id='spoof', authenticated=False, preferences=self.preferences('en'))
        with self.assertRaises(ProviderError):
            apply_verified_reply(self.c, p, 'spoof', now=NOW)
        self.assertEqual(self.c.db.execute('SELECT payload FROM contact_preferences WHERE address=?', ('alex@example.invalid',)).fetchone()[0], saved)

    def test_representative_locale_and_format_matrix_preserves_conditions_and_citation(self):
        source, original = self.source()
        for language in ('en', 'es'):
            for format in ('plain_text', 'structured_plain_text'):
                with self.subTest(language=language, format=format):
                    self.c.set_contact_preferences('alex@example.invalid', self.preferences(language, format), 'verified fixture preference', now=NOW)
                    result = self.c.accessible_evidence(question='Performers', address='alex@example.invalid', now=NOW)
                    self.assertIn(original, result['text'])
                    self.assertIn(source, result['text'])
                    self.assertIn('18:30', result['text'])
                    self.assertIn('cancelled', result['text'])
                    self.assertEqual(result['format'], format)
                    if language == 'es':
                        self.assertIn('Si se cancela el ensayo, no viajes.', result['text'])
                    else:
                        self.assertNotIn('Los artistas', result['text'])

    def test_changed_withdrawn_and_private_sources_do_not_reuse_translation(self):
        source, original = self.source()
        self.c.set_contact_preferences('alex@example.invalid', self.preferences(), 'verified fixture preference', now=NOW)
        self.c.ingest(original + ' Rehearsal now starts at 19:00.', source, 'Rehearsal guide', NOW)
        result = self.c.accessible_evidence(question='Performers', address='alex@example.invalid', now=NOW)
        self.assertIn('No hay traducción revisada', result['text'])
        self.assertNotIn('Los artistas', result['text'])
        self.c.withdraw_source(source, 'verified source withdrawal', now=NOW)
        self.c.ingest('Performers SECRET private notes.', 'private-guide', 'Private', NOW, 'coordinator')
        result = self.c.accessible_evidence(question='Performers', address='alex@example.invalid', now=NOW)
        self.assertEqual(result['evidence'], [])
        self.assertNotIn('SECRET', result['text'])
        self.assertIn('No encontré', result['text'])

    def test_unsupported_preferences_leave_supported_settings_unchanged(self):
        self.c.set_contact_preferences('alex@example.invalid', self.preferences(), 'verified fixture preference', now=NOW)
        for preferences in (self.preferences('fr'), self.preferences(format='audio')):
            with self.assertRaises(ValueError):
                self.c.set_contact_preferences('alex@example.invalid', preferences, 'verified preference', now=NOW)
        stored = self.c.db.execute('SELECT payload FROM contact_preferences WHERE address=?', ('alex@example.invalid',)).fetchone()[0]
        self.assertEqual(json.loads(stored), self.preferences())
