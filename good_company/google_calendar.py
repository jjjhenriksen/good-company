"""Single-account Google calendar reader using the owner's Latch connection."""
import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
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

    def check_availability(self, scope, start, end, now=None):
        """Owner-only free/busy check; never imports or returns event details.

        Construct a separate reader with the owner's selected calendar mapping;
        do not add personal calendars to the reminder scheduler's scopes.
        """
        if scope not in self.scopes:
            raise ProviderError('google_calendar_outside_scope')
        calendar_id = self.scopes[scope]
        if calendar_id == 'primary':
            calendar_id = self.email
        # gog also accepts names, indices and comma-separated lists. This path
        # permits only a single explicit Google calendar ID, never those selectors.
        if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+', calendar_id) or calendar_id.startswith('-'):
            raise ProviderError('explicit_availability_calendar_id_required')
        try:
            if not all(isinstance(value, str) and value.strip() for value in (start, end)):
                raise ValueError()
            start, end = iso(start), iso(end)
            if not timedelta(0) < stamp(end) - stamp(start) <= timedelta(days=93):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ProviderError('invalid_availability_window') from None
        self.account()
        data, observed = self._read(['plow-gog', 'calendar', 'freebusy', calendar_id,
                                    '--account', self.email, '--from', start, '--to', end, '--json'])
        if not timedelta(0) <= stamp(now) - stamp(observed) <= timedelta(minutes=15):
            raise ProviderError('availability_observation_not_current')
        calendars = data.get('calendars')
        if not isinstance(calendars, dict) or set(calendars) != {calendar_id}:
            raise ProviderError('availability_scope_unconfirmed')
        calendar = calendars[calendar_id]
        if not isinstance(calendar, dict) or set(calendar) - {'busy', 'errors'}:
            raise ProviderError('availability_result_unconfirmed')
        errors = calendar.get('errors', [])
        if not isinstance(errors, list) or errors:
            raise ProviderError('availability_calendar_unavailable')
        # gog's Go serializer omits an empty busy list. An explicitly present
        # calendar with no errors is required even for this empty result.
        busy = calendar.get('busy', [])
        if not isinstance(busy, list) or len(busy) > 10000:
            raise ProviderError('availability_intervals_unconfirmed')
        try:
            for interval in busy:
                if (not isinstance(interval, dict) or set(interval) != {'start', 'end'}
                        or not all(isinstance(value, str) and value.strip() for value in interval.values())):
                    raise ValueError()
                first, last = stamp(interval['start']), stamp(interval['end'])
                if not first < last or first >= stamp(end) or last <= stamp(start):
                    raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise ProviderError('availability_intervals_unconfirmed') from None
        return {'available': not busy, 'checked_at': observed,
                'message': 'There is an existing commitment.' if busy else 'No conflict in the checked window.',
                'scope': 'Selected calendar and requested window only; this does not reserve a time.'}

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
        title = GoogleCalendar._display_text(raw.get('summary'))
        if not isinstance(title, str) or not title.strip():
            raise ProviderError('google_missing_event_title')
        status = raw.get('status')
        if status not in ('confirmed', 'tentative', 'cancelled'):
            raise ProviderError('google_invalid_event_status')
        return {'id': uid, 'title': title, 'start': start, 'end': end,
                'all_day': all_day, 'status': status,
                'source': 'google-calendar://' + quote(calendar_id, safe='') + '/' + quote(uid, safe=''),
                'location': GoogleCalendar._display_text(raw.get('location', ''))}

    @staticmethod
    def _display_text(value):
        # Latch labels Google strings as untrusted source data. Remove only its
        # exact outer display envelope; the contents remain inert source text.
        # Never evaluate embedded instructions or relax owner scope from them.
        if not isinstance(value, str):
            raise ProviderError('google_invalid_text_field')
        if '<<<EXTERNAL_UNTRUSTED_CONTENT' not in value and '<<<END_EXTERNAL_UNTRUSTED_CONTENT' not in value:
            return value
        match = re.fullmatch(
            r'<<<EXTERNAL_UNTRUSTED_CONTENT id="([0-9a-f]{16,64})">>>\n'
            r'Source: google_api\n---\n([\s\S]*?)\n'
            r'<<<END_EXTERNAL_UNTRUSTED_CONTENT id="\1">>>', value)
        if not match or '<<<EXTERNAL_UNTRUSTED_CONTENT' in match[2] or '<<<END_EXTERNAL_UNTRUSTED_CONTENT' in match[2]:
            raise ProviderError('google_invalid_text_envelope')
        return match[2]
