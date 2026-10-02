"""Bounded exact-calendar Apple PIM reader; unsupported evidence fails closed."""
from dataclasses import replace
from datetime import date, datetime, time
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .apple_pim import ApplePIMReplies, source_text
from .core import digest, iso, required_time, stamp
from .providers import CalendarPage, ProviderError


class ApplePIMProvider(ApplePIMReplies):
    def __init__(self, *args, scopes, timezone='UTC', **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(scopes, dict) or not scopes or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in scopes.items()):
            raise ProviderError('apple_pim_explicit_calendars_required')
        self.scopes, self.timezone = dict(scopes), ZoneInfo(timezone)

    def account(self):
        account = super().account()
        data, _ = self.read('calendar', 'list')
        calendars = data.get('calendars')
        if data.get('success') is not True or not isinstance(calendars, list):
            raise ProviderError('apple_pim_calendar_access_unconfirmed')
        for calendar in self.scopes.values():
            if sum(isinstance(v, dict) and v.get('id') == calendar for v in calendars) != 1:
                raise ProviderError('apple_pim_calendar_not_authorized')
        return replace(account, calendar_scopes=frozenset(self.scopes), calendar_read=True)

    def calendar_page(self, scope, start, end, cursor=None):
        if scope not in self.scopes or cursor is not None:
            raise ProviderError('apple_pim_calendar_outside_scope')
        start, end = iso(required_time(start, 'window start')), iso(required_time(end, 'window end'))
        if stamp(start) >= stamp(end):
            raise ProviderError('invalid_calendar_window')
        # A sentinel above the domain's payload cap detects native prefix truncation.
        data, observed = self.read('calendar', 'events', **{'calendar': self.scopes[scope],
            'from': start, 'to': end, 'limit': 10001})
        events = data.get('events')
        if (data.get('success') is not True or not isinstance(events, list) or len(events) >= 10001
                or type(data.get('count')) is not int or data['count'] != len(events)
                or data.get('truncated') or data.get('degraded')):
            raise ProviderError('apple_pim_incomplete_calendar')
        normalized, cancellations = [], []
        for raw in events:
            event = self._event(raw, self.scopes[scope])
            if event['status'] == 'cancelled':
                cancellations.append(event)
                continue
            first = (datetime.combine(date.fromisoformat(event['start']), time.min, self.timezone)
                     if event.get('all_day') else stamp(event['start']))
            if stamp(start) <= first < stamp(end):
                normalized.append(event)
        return CalendarPage(scope, normalized, observed, True, True, cancellations=cancellations)

    def _event(self, raw, calendar):
        if not isinstance(raw, dict) or raw.get('calendarId') != calendar:
            raise ProviderError('apple_pim_event_outside_calendar')
        identifier = raw.get('id')
        if not isinstance(identifier, str) or not identifier.strip():
            raise ProviderError('apple_pim_missing_event_identity')
        if raw.get('recurrence') or raw.get('seriesId'):
            series, origin = raw.get('seriesId'), raw.get('occurrenceOrigin')
            if not isinstance(series, str) or not series or not isinstance(origin, str):
                raise ProviderError('apple_pim_missing_occurrence_origin')
            try:
                origin = iso(required_time(origin, 'original occurrence'))
            except (ValueError, TypeError):
                raise ProviderError('apple_pim_missing_occurrence_origin') from None
            identifier = digest([calendar, series, origin])
        source = 'apple-calendar://' + quote(calendar, safe='') + '/' + quote(identifier, safe='')
        if raw.get('status') == 'cancelled':
            return {'id': identifier, 'status': 'cancelled', 'source': source}
        all_day = raw.get('isAllDay')
        if type(all_day) is not bool:
            raise ProviderError('apple_pim_missing_all_day_evidence')
        try:
            if all_day:
                # UTC display timestamps alone do not establish a floating date.
                first, last = raw['allDayStart'], raw['allDayEnd']
                if date.fromisoformat(first) >= date.fromisoformat(last):
                    raise ValueError()
            else:
                first, last = iso(required_time(raw['startDate'], 'event start')), iso(required_time(raw['endDate'], 'event end'))
                if stamp(first) >= stamp(last):
                    raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ProviderError('apple_pim_invalid_event_time') from None
        title = source_text(raw.get('title'), 'calendar')
        if not title.strip():
            raise ProviderError('apple_pim_missing_event_title')
        return {'id': identifier, 'source': source, 'title': title, 'start': first, 'end': last,
                'all_day': all_day, 'status': 'confirmed',
                'location': source_text(raw.get('location', ''), 'calendar')}

    def availability(self, scope, start, end):
        # Native EventKit windows include overlapping events; preserve that
        # behavior here rather than the domain snapshot's start-window filter.
        if scope not in self.scopes:
            raise ProviderError('apple_pim_calendar_outside_scope')
        first, last = required_time(start, 'window start'), required_time(end, 'window end')
        if first >= last:
            raise ProviderError('invalid_calendar_window')
        self.account()
        data, observed = self.read('calendar', 'events', **{'calendar': self.scopes[scope],
            'from': iso(first), 'to': iso(last), 'limit': 10001})
        raw = data.get('events')
        if (data.get('success') is not True or not isinstance(raw, list) or len(raw) >= 10001
                or type(data.get('count')) is not int or data['count'] != len(raw)
                or data.get('truncated') or data.get('degraded')):
            raise ProviderError('apple_pim_incomplete_calendar')
        busy = False
        for item in raw:
            event = self._event(item, self.scopes[scope])
            if event['status'] == 'cancelled':
                continue
            if event.get('all_day'):
                event_start = datetime.combine(date.fromisoformat(event['start']), time.min, self.timezone)
                event_end = datetime.combine(date.fromisoformat(event['end']), time.min, self.timezone)
            else:
                event_start, event_end = stamp(event['start']), stamp(event['end'])
            busy |= event_start < last and event_end > first
        return {'available': not busy, 'checked_at': observed,
                'message': 'There is an existing commitment.' if busy else 'No conflict in the checked window.',
                'scope': 'Selected calendar/window only; no title, recipient or booking authority is disclosed.'}

    def send(self, message, operation_id, idempotency_key=None):
        raise ProviderError('apple_pim_send_receipt_unavailable')

    def reconcile(self, operation_id):
        raise ProviderError('apple_pim_send_reconciliation_unavailable')
