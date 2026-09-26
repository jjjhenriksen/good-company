"""Owner-session setup. Connected tools establish identity; this stores the remit."""
import json
from .core import digest, required, stamp
from .tasks import WorkCoordinator
from .corrections import CorrectionCoordinator


class SetupCoordinator(CorrectionCoordinator):
    def onboarding(self, profile=None, policy=None, authority=None, apply=False):
        """Preview a complete remit before applying it in one transaction.

        The agent translates the owner's conversation into these existing schemas.
        Preview never changes authority or enables a scheduler.
        """
        if type(apply) is not bool:
            raise ValueError('apply must be true or false.')
        if profile is None or policy is None:
            return {'status': 'needs_context', 'questions': [
                'What is your organization called, and which timezone do you use?',
                'Which exact calendar scope, event categories and tasks should I coordinate?',
                'Which connected sending account and verified recipients may I use?',
                'When should reminders arrive, and how should I greet and sign off to your group?',
                'Which supplied sources should I consult?'],
                'next': 'Use connected tools to verify account and audience; never infer addresses or copy the demo remit.'}
        required(authority, 'owner instruction reference')
        # Existing validation and invalidation run in an isolated database first.
        # The live DB changes only after all validation has succeeded.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            candidate = WorkCoordinator(Path(directory) / 'candidate.sqlite')
            try:
                candidate.configure(profile)
                candidate.configure_autonomy(policy, authority)
            finally:
                candidate.db.close()
        if not set(profile['reminder_days']) <= set(policy['cadence_days']):
            raise ValueError('Profile reminder days must be allowed by the standing remit.')
        preview = {'organization': profile['organization'], 'timezone': profile['timezone'],
                   'profile': profile, 'standing_remit': policy,
                   'message': 'Settings prepared. Connection, scheduler and delivery still require observed evidence.'}
        if not apply:
            return {'status': 'preview', 'preview': preview}
        now = stamp()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            previous_profile = self.db.execute("SELECT value FROM settings WHERE key='profile'").fetchone()
            changed = (not previous_profile or json.loads(previous_profile[0]) != profile
                       or self.autonomy() != policy)
            if changed:
                for row in self.db.execute('SELECT id FROM events').fetchall():
                    self._invalidate(row['id'])
                for key, value in [('profile', profile), ('autonomy', policy)]:
                    self.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (key, json.dumps(value)))
                self.log('standing_instructions', 'autonomy',
                         {'authority': authority, 'policy_hash': digest(policy)}, now)
                self.log('onboarding_applied', 'organization', {'authority': authority}, now)
        return {'status': 'configured', 'preview': preview, 'changed': changed,
                'next': 'Preview a sourced answer or event, then verify the connected scheduler and delivery.'}
