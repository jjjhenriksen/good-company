"""Private operator health summaries; no delivery side effects."""
import json
from .core import digest


def report(coordinator, now=None):
    state = coordinator.readiness(now=now)
    # Observation timestamps are useful context, but refreshing the same failure
    # must not generate another alert. Fingerprint actionable states only.
    health = {'ready': state['ready'], 'actions': state['reasons'],
              'connections': {key: value['status'] for key, value in state['connections'].items()},
              'calendar_fresh': state['calendar']['fresh'], 'sources': state['sources'],
              'latest_cycle': {key: state['latest_cycle'][key] for key in ('status', 'planning_exceptions')},
              'delivery': state['delivery'], 'unresolved_exceptions': state['unresolved_exceptions']}
    fingerprint = digest({key: value for key, value in health.items() if key != 'delivery'} |
                         {'delivery_failures': {key: state['delivery'][key] for key in ('unknown', 'failed')}})
    with coordinator.db:
        coordinator.db.execute('BEGIN IMMEDIATE')
        prior = coordinator.db.execute("SELECT value FROM settings WHERE key='health:last'").fetchone()
        changed = not prior or prior[0] != fingerprint
        coordinator.db.execute("INSERT OR REPLACE INTO settings VALUES('health:last',?)", (fingerprint,))
    return {'health': health, 'changed': changed,
            'notify': changed and (not health['ready'] or prior is not None),
            'last_scheduler_observation': state['connections']['scheduler']['last_observed'],
            'scope': 'Local state and trusted observations. A notification recommendation is not a sent alert.'}
