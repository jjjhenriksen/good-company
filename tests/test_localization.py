import unittest
from good_company.localization import date_text, time_text
from test_onboarding import OnboardingTests


class LocalizationTests(OnboardingTests):
    def test_terms_and_locale_persist_without_expanding_authority(self):
        self.c.onboarding(self.profile, self.policy, 'owner', True)
        self.profile.update(locale='en-GB', terminology={'coordinator': 'production lead', 'task': 'call'})
        self.c.configure(self.profile)
        self.assertEqual(self.c.profile()['terminology']['task'], 'call')
        self.assertEqual(self.c.autonomy(), self.policy)

    def test_london_dst_offsets_disambiguate_repeated_hour(self):
        profile = {'timezone': 'Europe/London', 'locale': 'en-GB'}
        self.assertEqual(date_text('2026-10-25T00:30:00Z',profile), 'Sunday, 25 October 2026')
        self.assertIn('01:30 BST (UTC+0100)', time_text('2026-10-25T00:30:00Z',profile))
        self.assertIn('01:30 GMT (UTC+0000)', time_text('2026-10-25T01:30:00Z',profile))

    def test_unsupported_locale_preserves_profile(self):
        self.c.configure(self.profile)
        changed = dict(self.profile, locale='invented')
        with self.assertRaises(ValueError): self.c.configure(changed)
        self.assertEqual(self.c.profile(), self.profile)
