"""Single-account Google calendar reader using the owner's Latch connection."""
import hashlib
import json
from datetime import date, datetime, time
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .core import iso, stamp
from .providers import Account, CalendarPage, ProviderError


class GoogleCalendar:
    """Read-only provider. Reuse cycle_id when resuming an interrupted refresh.

    scopes maps owner-authorized domain scope names to exact Google calendar IDs.
    No calendar or account is selected implicitly; no fan-out or query filtering.
    """
    def __init__(self, operations, account, scopes, cycle_id, timezone='UTC'):
        if not isinstance(account, str) or '@' not in account or not account.strip() == account:
            raise ProviderError('explicit_google_account_required')
        if not isinstance(scopes, dict) or not scopes or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in scopes.items()):
            raise ProviderError('explicit_google_scopes_required')
        if not isinstance(cycle_id, str) or not cycle_id.strip():
            raise ProviderError('calendar_cycle_required')
        self.operations, self.email, self.scopes = operations, account, dict(scopes)
        self.cycle_id, self.timezone = cycle_id, timezone
        ZoneInfo(timezone)

    def _read(self, argv):
        key = hashlib.sha256(json.dumps([self.cycle_id, argv]).encode()).hexdigest()
        operation = 'google-read:' + key
        result = self.operations.execute(operation, argv, 'Read the authorized Google account and scoped calendar for Good Company.')
        if result['state'] in ('pending', 'running'):
            result = self.operations.poll(operation)
        payload = result.get('result') or {}
        if result['state'] != 'completed':
            raise ProviderError('google_read_' + result['state'])
        # The accounts command is handled directly by Latch rather than a child
        # process. Its structured completed result has no process exit code.
        if argv == ['plow-gog', 'accounts'] and isinstance(payload.get('accounts'), list):
            data = payload
        else:
            if type(payload.get('exit_code')) is not int or payload['exit_code'] != 0:
                raise ProviderError('google_read_failed')
            output = payload.get('output')
            if not isinstance(output, str):
                raise ProviderError('google_missing_output')
            # gog writes a known token-lifetime notice before JSON. Accept only
            # this exact non-data prefix, never search arbitrarily for a brace.
            prefix = 'Note: Using direct access token (expires in ~1 hour; no auto-refresh)\n'
            if output.startswith(prefix):
                output = output[len(prefix):]
            try:
                data = json.loads(output)
            except ValueError:
                raise ProviderError('google_invalid_json') from None
        if not isinstance(data, dict) or data.get('degraded') or data.get('truncated') or data.get('error'):
            raise ProviderError('google_incomplete_result')
        observed = payload.get('_received_at')
        if not observed:
            raise ProviderError('google_missing_observation_time')
        return data, iso(observed)

    def account(self):
        data, _ = self._read(['plow-gog', 'accounts'])
        matches = [a for a in data['accounts'] if a.get('account') == self.email]
        if len(matches) != 1 or any(matches[0].get(k) for k in ('unavailable', 'error', 'unavailability')):
            raise ProviderError('google_account_unavailable')
        return Account('google-latch', self.email, self.email, True,
                       frozenset(self.scopes), True, False)

    def calendar_page(self, scope, start, end, cursor=None):
        if scope not in self.scopes:
            raise ProviderError('google_calendar_outside_scope')
        start, end = iso(start), iso(end)
        if stamp(start) >= stamp(end):
            raise ProviderError('invalid_calendar_window')
        argv = ['plow-gog', 'calendar', 'events', self.scopes[scope],
                '--account', self.email, '--from', start, '--to', end,
                '--max', '100', '--json']
        if cursor is not None:
            if not isinstance(cursor, str) or not cursor:
                raise ProviderError('invalid_google_page_cursor')
            argv += ['--page', cursor]
        data, observed = self._read(argv)
        # Require the raw single-calendar envelope. Fan-out compact events lack
        # recurrence and completeness evidence and must never be imported.
        if not isinstance(data.get('events'), list) or 'nextPageToken' not in data:
            raise ProviderError('google_missing_calendar_envelope')
        token = data['nextPageToken']
        if token is not None and not isinstance(token, str):
            raise ProviderError('invalid_google_page_cursor')
        events = []
        for raw in data['events']:
            event = self._event(raw, self.scopes[scope])
            # Google timeMin filters event END; the domain snapshot filters START.
            event_start = (datetime.combine(date.fromisoformat(event['start']), time.min, ZoneInfo(self.timezone))
                           if event.get('all_day') else stamp(event['start']))
            if stamp(start) <= event_start < stamp(end):
                events.append(event)
        return CalendarPage(scope, events, observed, True, True, token or None)

    @staticmethod
    def _event(raw, calendar_id):
        if not isinstance(raw, dict) or raw.get('recurrence'):
            raise ProviderError('google_unexpanded_event')
        uid = raw.get('id')
        if not isinstance(uid, str) or not uid.strip():
            raise ProviderError('google_missing_instance_id')
        if raw.get('recurringEventId') and not raw.get('originalStartTime'):
            raise ProviderError('google_missing_occurrence_origin')
        first, last = raw.get('start', {}), raw.get('end', {})
        if not isinstance(first, dict) or not isinstance(last, dict):
            raise ProviderError('google_invalid_event_time')
        all_day = bool(first.get('date'))
        try:
            if all_day:
                start, end = first['date'], last['date']
                if date.fromisoformat(start) >= date.fromisoformat(end):
                    raise ValueError()
            else:
                start, end = iso(first['dateTime']), iso(last['dateTime'])
                if stamp(start) >= stamp(end):
                    raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise ProviderError('google_invalid_event_time') from None
        title = raw.get('summary')
        if not isinstance(title, str) or not title.strip():
            raise ProviderError('google_missing_event_title')
        status = raw.get('status')
        if status not in ('confirmed', 'tentative', 'cancelled'):
            raise ProviderError('google_invalid_event_status')
        return {'id': uid, 'title': title, 'start': start, 'end': end,
                'all_day': all_day, 'status': status,
                'source': 'google-calendar://' + quote(calendar_id, safe='') + '/' + quote(uid, safe=''),
                'location': raw.get('location', '')}
