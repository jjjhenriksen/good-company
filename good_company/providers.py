"""Provider boundary. Implementations must use actual authenticated connected tools.

The fixtures implement this protocol; they are never evidence of live delivery.
"""
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4
from .core import required, stamp, iso


class ProviderError(ValueError):
    """Explicit safe error code, without provider response bodies or credentials."""


@dataclass(frozen=True)
class Account:
    provider: str
    account_id: str
    sender: str
    authenticated: bool
    calendar_scopes: frozenset[str]
    calendar_read: bool
    unattended_send: bool
    idempotent_send: bool = False
    reconcile_send: bool = False


@dataclass(frozen=True)
class CalendarPage:
    scope: str
    events: list[dict]
    checked_at: str
    expanded: bool
    complete_page: bool
    next_cursor: str | None = None


@dataclass(frozen=True)
class SendResult:
    outcome: str  # accepted, failed, unknown
    reference: str  # actual receipt for accepted; safe error/evidence reference otherwise


class Provider(Protocol):
    def account(self) -> Account: ...
    def calendar_page(self, scope: str, start: str, end: str, cursor: str | None) -> CalendarPage: ...
    def send(self, message: dict, operation_id: str, idempotency_key: str | None) -> SendResult: ...
    def reconcile(self, operation_id: str) -> SendResult: ...


def authenticated_account(provider):
    account = provider.account()
    if not account.authenticated:
        raise ProviderError('unauthenticated_account')
    required(account.provider, 'provider identity')
    required(account.account_id, 'authenticated account identity')
    return account


def import_complete_calendar(coordinator, provider, scope, start, end, now=None):
    account = authenticated_account(provider)
    if not account.calendar_read or scope not in account.calendar_scopes:
        raise ProviderError('calendar_permission_denied')
    policy = coordinator.autonomy()
    if not policy or scope not in policy['calendar_scopes']:
        raise ProviderError('calendar_outside_standing_scope')
    fixed_now = stamp(now) if now is not None else None
    start, end = iso(start), iso(end)
    events, cursors, cursor, checked = [], set(), None, None
    for _ in range(1000):
        page = provider.calendar_page(scope, start, end, cursor)
        if page.scope != scope or not page.expanded or not page.complete_page:
            raise ProviderError('incomplete_or_unscoped_calendar')
        try:
            observed = stamp(required(page.checked_at, 'calendar observation time'))
        except (ValueError, TypeError):
            raise ProviderError('invalid_calendar_observation') from None
        if observed > (fixed_now or stamp()):
            raise ProviderError('future_calendar_observation')
        checked = min(checked, observed) if checked else observed
        events.extend(page.events)
        if len(events) > 10000:
            raise ProviderError('calendar_payload_limit')
        if page.next_cursor is None:
            return coordinator.import_calendar({'calendar': scope, 'window_start': start, 'window_end': end,
                                                'checked_at': iso(checked), 'complete': True, 'events': events}, now=fixed_now or stamp())
        if not page.next_cursor or page.next_cursor in cursors:
            raise ProviderError('invalid_calendar_pagination')
        cursors.add(page.next_cursor)
        cursor = page.next_cursor
    raise ProviderError('calendar_page_limit')


class Delivery:
    """Claim once before calling the provider, then persist a truthful outcome."""
    def __init__(self, coordinator, provider):
        self.coordinator, self.provider = coordinator, provider
        coordinator.db.execute('''CREATE TABLE IF NOT EXISTS provider_operations(
          kind TEXT NOT NULL, notice_id TEXT NOT NULL, provider TEXT NOT NULL, account_id TEXT NOT NULL,
          PRIMARY KEY(kind,notice_id))''')

    def _methods(self, kind):
        c = self.coordinator
        if kind == 'event':
            return c.claim, c.receipt, 'rid'
        if kind == 'task':
            return c.task_claim, c.task_receipt, 'notice_id'
        if kind == 'correction':
            return c.correction_claim, c.correction_receipt, 'correction_id'
        raise ProviderError('unknown_notice_kind')

    def _record(self, kind, notice_id, result, now):
        _, receipt, parameter = self._methods(kind)
        if not isinstance(result, SendResult) or result.outcome not in ('accepted', 'failed', 'unknown') or not isinstance(result.reference, str) or not result.reference.strip():
            result = SendResult('unknown', 'invalid-provider-result:' + uuid4().hex)
        outcome = {'accepted': 'sent', 'failed': 'failed', 'unknown': 'uncertain'}[result.outcome]
        return receipt(**{parameter: notice_id}, outcome=outcome, provider_id=result.reference, now=now)

    def send(self, kind, notice_id, now=None):
        account = authenticated_account(self.provider)
        policy = self.coordinator.autonomy()
        if not account.unattended_send or not policy or not policy.get('enabled') or account.sender != policy['sender']:
            raise ProviderError('unattended_sender_permission_denied')
        claim, _, parameter = self._methods(kind)
        payload = claim(**{parameter: notice_id}, now=now)
        with self.coordinator.db:
            self.coordinator.db.execute('INSERT INTO provider_operations VALUES(?,?,?,?)', (kind, notice_id, account.provider, account.account_id))
        operation_id = kind + ':' + notice_id
        try:
            result = self.provider.send(payload['message'], operation_id,
                                        operation_id if account.idempotent_send else None)
        except Exception:
            # A transport exception can occur after provider acceptance. Do not retry.
            result = SendResult('unknown', 'transport-unconfirmed:' + operation_id)
        return self._record(kind, notice_id, result, now)

    def reconcile(self, kind, notice_id, now=None):
        account = authenticated_account(self.provider)
        operation = self.coordinator.db.execute('SELECT provider,account_id FROM provider_operations WHERE kind=? AND notice_id=?', (kind, notice_id)).fetchone()
        if not account.reconcile_send or not operation or tuple(operation) != (account.provider, account.account_id):
            raise ProviderError('reconciliation_unavailable_or_wrong_account')
        result = self.provider.reconcile(kind + ':' + notice_id)
        return self._record(kind, notice_id, result, now)
