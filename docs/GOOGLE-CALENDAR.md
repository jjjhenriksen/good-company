# Google calendar adapter

`good_company.google_calendar.GoogleCalendar` implements the account and calendar
read portion of the existing provider contract through authenticated Plow Latch.
It does not send mail. Its Account explicitly reports `unattended_send=False`.

Provide the connected account email, an owner-authorized mapping of domain scope
names to exact Google calendar IDs, and a unique refresh cycle ID. Keep that cycle
ID when resuming after a restart; use a new one for a genuinely new refresh.
The mapping does not itself grant a standing remit: `import_complete_calendar`
also checks the coordinator's authorized scopes before applying a snapshot.

The reader invokes the current `plow-gog` command through `LatchOperations`.
It requests one account and one calendar, capped at 100 instances per page, and
preserves each page token. Combined-account results, missing pagination metadata,
degraded/truncated output and unexpanded recurring masters are rejected. No
partial result replaces saved calendar state. Original observation timestamps
remain attached to cached pages, so reopening an old operation cannot make it
look newly refreshed.

The bundled gog v0.36.0 source at commit `eaa5d631` uses `SingleEvents(true)` and
`ShowDeleted(false)` in its [calendar list implementation](https://github.com/steipete/gogcli/blob/eaa5d631/internal/cmd/calendar_list.go).
Expanded instances retain their Google instance IDs when moved. Deletions are
reflected through absence in a complete scoped snapshot. Google lists events
overlapping the requested window; the adapter filters to starts within the domain
snapshot window. Multi-day all-day events retain their exclusive end date rather
than becoming a one-day event. These times still do not imply a known meeting hour.

## Verification and remaining work

Tests cover exact account/calendar selection, pagination, original observation
time on restart, fresh cycle IDs, incomplete output rejection, recurring-instance
identity, timezone validation, overlapping events and multi-day imports. Existing
contract tests cover atomic import and duplicate occurrence rejection.

The first live attempt on 2026-09-26 was denied at account discovery under the
family-assistant remit. After the owner authorized a temporary, exact read-only
exception, the deployed adapter completed both account discovery and the existing
fictional event's one-hour calendar query. Latch recorded both requests allowed
and completed. One complete page containing the expected non-recurring event was
normalized and imported into an isolated, paused acceptance database. The original
Gatekeeper policy was restored immediately afterward; Gatekeeper stayed enabled.

[Sanitized live evidence](../eval/providers/google-calendar-live.json) records the
actual source/image, observation time and outcome. Reopening the private operation
journal with a transport that refuses every call still returned the authenticated
account and same calendar page: the two completed operations were reused without
redispatch. The observation timestamp was preserved. No mail or calendar write
occurred. This proves a real scoped single-page read, not live recurrence,
multi-page completeness, scheduled delivery, or unattended authority.

That observed response also exposed a transport bug: `isError` envelopes can carry
an explicit `denied` or `blocked` result. Those states and their reason are now
preserved in the private journal, without retry. Structured account completions
are supported without pretending they have a child-process exit code; ordinary
calendar command output still requires an actual zero exit code and valid JSON.

The combined [Google adapter acceptance record](GOOGLE-ADAPTER-VALIDATION.md)
now includes contract coverage for multi-page recurring imports and live scheduled
mail delivery/reconciliation. Live calendar evidence remains single-page and
non-recurring; the lifecycle matrix in #9 is separate.

## Owner context for imported events

Google event titles do not establish organization categories or dress requirements.
The standing remit can now include optional `event_contexts`, keyed by the exact
authorized domain calendar scope and provider instance ID. The agent records these
from explicit owner instructions during setup; the owner need not edit JSON.
Each context requires a participant-safe source reference and may supply
`event_type`, `dress_applicability`, `program`, `dress_code_role`,
`mixed_role_audience`, or a fallback `location`. Event type must already be allowed
by the remit. No wildcard, inferred title match, recipient override, time override
or cancellation override is supported.

The core importer reapplies this cited context on each complete refresh. A location
from the calendar takes precedence; owner context only fills an absent location.
The calendar source remains attached, and the owner reference is added separately.
Removing/changing the context invalidates pending approvals through the existing
remit update; the next refresh rebuilds from provider facts. Withdrawing its source
prevents automatic authorization. This mechanism supplies missing organizational
context; it does not grant provider access or unattended-send permission.
