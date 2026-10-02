"""One bounded operational cycle for the owner's existing runtime scheduler."""
from contextlib import contextmanager
import fcntl
import json
import os

from .core import digest, iso, stamp, required_time
from .providers import Delivery, ProviderError, authenticated_account, import_complete_calendar


@contextmanager
def cycle_lock(coordinator):
    filename = coordinator.db.execute('PRAGMA database_list').fetchone()[2]
    if not filename:
        raise ProviderError('cycle_requires_durable_database')
    fd = os.open(filename + '.cycle.lock', os.O_CREAT | os.O_RDWR, 0o600)
    locked = False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except BlockingIOError:
            pass
        yield locked
    finally:
        if locked:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def run_cycle(coordinator, provider, cycle_id, start, end, now=None):
    """Refresh every scope, plan, allocate, reconcile and send due work once.

    now exists solely for library tests. Production entrypoints use the real clock.
    A new cadence tick uses a new cycle_id; resume interrupted ticks with the same
    ID and window so durable provider operations retain their handles.
    """
    if not isinstance(cycle_id, str) or not cycle_id.strip() or len(cycle_id) > 128:
        raise ProviderError('invalid_cycle_id')
    start, end = iso(required_time(start, 'window start')), iso(required_time(end, 'window end'))
    if not 0 < (stamp(end) - stamp(start)).total_seconds() <= 93 * 86400:
        raise ProviderError('invalid_cycle_window')
    with cycle_lock(coordinator) as locked:
        if not locked:
            return {'status': 'already_running', 'cycle_id': cycle_id}
        if hasattr(coordinator, 'expire_module_records'):
            coordinator.expire_module_records('configured workflow retention', now=now)
        policy = coordinator.autonomy()
        if not policy or not policy.get('enabled'):
            return {'status': 'paused', 'cycle_id': cycle_id}
        db = coordinator.db
        attempt_started = iso(stamp(now))

        def observe(status, planning_exceptions=0):
            observed = stamp(now)
            coordinator.log('cycle_observed', digest(cycle_id)[:24],
                            {'status': status, 'started_at': attempt_started,
                             'finished_at': None if status == 'running' else iso(observed),
                             'planning_exceptions': planning_exceptions}, observed)

        with db:
            observe('running')
        try:
            account = authenticated_account(provider)
        except ProviderError:
            with db:
                observe('blocked')
            return {'status': 'blocked', 'cycle_id': cycle_id, 'reason': 'provider_identity_unavailable'}
        modules = [list(r) for r in db.execute('SELECT module,payload FROM module_policies ORDER BY module')] if hasattr(coordinator, 'module_queue') else []
        fingerprint = digest([start, end, policy, modules, coordinator.profile(), account.provider,
                              account.account_id, account.sender, sorted(account.calendar_scopes),
                              getattr(provider, 'scopes', None)])
        db.execute('''CREATE TABLE IF NOT EXISTS operational_cycles(
            id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
            started_at TEXT NOT NULL, finished_at TEXT, summary TEXT)''')
        with db:
            db.execute('INSERT OR IGNORE INTO operational_cycles VALUES(?,?,?, ?,NULL,NULL)',
                       (cycle_id, fingerprint, 'running', iso(stamp(now))))
        row = db.execute('SELECT * FROM operational_cycles WHERE id=?', (cycle_id,)).fetchone()
        if row['fingerprint'] != fingerprint:
            with db:
                observe('blocked')
            raise ProviderError('cycle_configuration_changed')
        if row['status'] == 'completed':
            saved = json.loads(row['summary'])
            with db:
                observe('completed', saved.get('planning_exceptions', 0))
            return saved | {'replayed': True}
        summary = {'cycle_id': cycle_id, 'status': 'running', 'refreshed_scopes': 0,
                   'sent': 0, 'uncertain': 0, 'failed': 0, 'reconciled': 0, 'deferred': 0,
                   'planning_exceptions': 0}

        def finish(status, reason=None):
            summary['status'] = status
            if reason:
                summary['reason'] = reason
            with db:
                db.execute('UPDATE operational_cycles SET status=?,finished_at=?,summary=? WHERE id=?',
                           (status, iso(stamp(now)), json.dumps(summary), cycle_id))
                observe(status, summary['planning_exceptions'])
            return summary

        try:
            if account.sender != policy['sender'] or not account.unattended_send:
                return finish('blocked', 'unattended_sender_permission_unverified')
            if not policy['calendar_scopes']:
                return finish('blocked', 'calendar_scope_missing')
            for scope in policy['calendar_scopes']:
                import_complete_calendar(coordinator, provider, scope, start, end, now=now)
                summary['refreshed_scopes'] += 1
        except ProviderError:
            return finish('blocked', 'provider_refresh_unavailable')
        except (ValueError, KeyError, TypeError):
            return finish('blocked', 'calendar_refresh_invalid')

        planned = coordinator.plan(now=now)
        allocated = coordinator.delegate(now=now)
        summary['planning_exceptions'] = len(planned.get('exceptions', [])) + len(allocated.get('exceptions', []))
        delivery = Delivery(coordinator, provider)
        queues = [('event', coordinator.queue()), ('task', coordinator.task_queue()),
                  ('correction', coordinator.correction_queue())]
        if hasattr(coordinator, 'module_queue'):
            queues.append(('module', coordinator.module_queue()))
        for kind, notices in queues:
            for notice in notices:
                # Every send still goes through the domain's current authority,
                # due-time, freshness, consent and communication-budget checks.
                attempted = notice['status'] in ('sending', 'uncertain')
                due = notice.get('due', notice.get('created_at'))
                ready = notice['status'] == ('approved' if kind == 'event' else 'pending')
                if not attempted and (not ready or (due and stamp(due) > stamp(now))):
                    continue
                try:
                    result = (delivery.reconcile(kind, notice['id'], now=now) if attempted
                              else delivery.send(kind, notice['id'], now=now))
                    status = result['status']
                    if attempted and status == 'sent':
                        summary['reconciled'] += 1
                    elif status in ('sent', 'uncertain', 'failed'):
                        summary[status] += 1
                except (ValueError, KeyError, TypeError):
                    # Quiet hours, changed authority, denied identity, unknown
                    # handles or another claim leave the domain ledger intact.
                    summary['deferred'] += 1
        return finish('completed')
