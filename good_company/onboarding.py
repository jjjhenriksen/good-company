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

    def record_connection(self, component, status, evidence, checked_at, now=None):
        """Record a trusted operator's observed tool outcome, never credentials.

        This is an audit attestation, not independent provider authentication.
        Evidence stays private; readiness returns only state and observation time.
        """
        from datetime import timedelta
        if component not in ('calendar', 'mail', 'scheduler'):
            raise ValueError('Component must be calendar, mail, or scheduler.')
        if status not in ('verified', 'unavailable', 'unknown', 'missing_credentials'):
            raise ValueError('Unknown connection status.')
        required(evidence, 'private observation reference')
        now, checked = stamp(now), stamp(checked_at)
        if checked > now or now - checked > timedelta(minutes=15):
            raise ValueError('Record a current observation, no more than 15 minutes old.')
        value = {'status': status, 'checked_at': checked.isoformat(),
                 'policy_hash': digest(self.autonomy()), 'evidence': evidence}
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',
                            ('connection:' + component, json.dumps(value)))
        return {'component': component, 'status': status}

    def readiness(self, now=None):
        from datetime import timedelta
        now = stamp(now)
        policy = self.autonomy()
        reasons, connections = [], {}
        configured = self.db.execute("SELECT 1 FROM settings WHERE key='profile'").fetchone() is not None
        if not configured:
            reasons.append('Set up your organization.')
        if not policy or not policy.get('enabled'):
            reasons.append('Standing coordination instructions are missing or paused.')
        for component in ('calendar', 'mail', 'scheduler'):
            row = self.db.execute('SELECT value FROM settings WHERE key=?', ('connection:' + component,)).fetchone()
            item = json.loads(row[0]) if row else {}
            status = item.get('status', 'unverified')
            if item and (stamp(item['checked_at']) > now or now - stamp(item['checked_at']) > timedelta(minutes=30)):
                status = 'stale'
            if item and item['policy_hash'] != digest(policy):
                status = 'unverified'
            connections[component] = {'status': status, 'last_observed': item.get('checked_at')}
            if status != 'verified':
                reasons.append(f'Verify the {component} connection or execution.')
        scopes = (policy or {}).get('calendar_scopes', [])
        refreshes = []
        for scope in scopes:
            row = self.db.execute('SELECT checked_at FROM calendar_sync WHERE calendar=?', (scope,)).fetchone()
            refreshes.append(row[0] if row else None)
        fresh = bool(refreshes) and all(value and timedelta(0) <= now - stamp(value) <= timedelta(minutes=15) for value in refreshes)
        if not fresh:
            reasons.append('Refresh every authorized calendar scope completely.')
        source_dates = [r[0] for r in self.db.execute('SELECT max(updated) FROM knowledge GROUP BY source')]
        stale_sources = sum(stamp(value) > now or now - stamp(value) > timedelta(days=180) for value in source_dates)
        if stale_sources:
            reasons.append('Review stale document sources.')
        source_state = {'documents': len(source_dates), 'stale': stale_sources,
                        'status': 'not_supplied' if not source_dates else ('needs_review' if stale_sources else 'current')}
        counts = {}
        for table in ('reminders', 'task_notices', 'corrections'):
            for row in self.db.execute(f'SELECT status,count(*) FROM {table} GROUP BY status'):
                counts[row[0]] = counts.get(row[0], 0) + row[1]
        exceptions = counts.get('draft', 0) + counts.get('failed', 0) + counts.get('uncertain', 0) + counts.get('sending', 0)
        if exceptions:
            reasons.append('Resolve draft, failed or uncertain notices.')
        return {'ready': not reasons, 'reasons': reasons, 'connections': connections,
                'sources': source_state,
                'calendar': {'fresh': fresh, 'last_complete_refresh': min(refreshes) if refreshes and all(refreshes) else None},
                'delivery': {'queued': counts.get('draft', 0) + counts.get('approved', 0) + counts.get('pending', 0),
                             'provider_accepted': counts.get('sent', 0),
                             'unknown': counts.get('sending', 0) + counts.get('uncertain', 0),
                             'failed': counts.get('failed', 0)},
                'unresolved_exceptions': exceptions,
                'scope': 'Trusted operator observations and local ledger; provider acceptance does not prove receipt by a person.'}

    def health(self, now=None):
        from .health import report
        return report(self, now)
