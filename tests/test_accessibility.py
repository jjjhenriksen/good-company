from test_contact_preferences import PreferenceTests
from test_core import NOW
from good_company.core import stamp


class AccessibleEvidenceTests(PreferenceTests):
    def test_reviewed_translation_keeps_original_conditions_and_rejects_changed_source(self):
        text='Performers arrive at 18:00 on 27 September. Guests arrive at 18:30.'
        self.c.ingest(text,'guide','Guide',NOW)
        item=self.c.retrieve('Performers',now=NOW)['evidence'][0]
        self.c.register_translation(source='guide',section=item['section'],original=text,translated='Los artistas llegan a las 18:00 el 27 de septiembre. Los invitados llegan a las 18:30.',language='es',authority='bilingual reviewer',now=NOW)
        self.c.set_contact_preferences('alex@example.invalid',self.prefs(language='es',format='structured_plain_text'),'verified preference',now=NOW)
        item=self.c.accessible_evidence(question='Performers',address='alex@example.invalid',now=NOW)['evidence'][0]
        self.assertEqual(item['original'],text);self.assertEqual(item['translation_status'],'reviewed')
        self.c.ingest(text+' Exception: cancelled when the venue closes.','guide','Guide',NOW)
        item=self.c.accessible_evidence(question='Performers',address='alex@example.invalid',now=NOW)['evidence'][0]
        self.assertEqual(item['translation_status'],'unavailable_original_retained')
        with self.assertRaisesRegex(ValueError,'reviewed language'):
            self.c._check_contacts({'to':['alex@example.invalid']},stamp(NOW))

    def test_unsupported_language_and_format_are_explicit(self):
        with self.assertRaises(ValueError):self.c.set_contact_preferences('alex@example.invalid',self.prefs(language='zz'),'verified',now=NOW)
        with self.assertRaises(ValueError):self.c.set_contact_preferences('alex@example.invalid',self.prefs(format='invented'),'verified',now=NOW)
