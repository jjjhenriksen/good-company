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

Live validation attempted on 2026-09-26 stopped at account discovery. Gatekeeper
denied `plow-gog accounts` under its existing family-assistant remit, interpreting
the account listing as potentially exposing account credentials. The calendar
query was never dispatched, and no mail or calendar mutation occurred. The new
reader therefore has contract-test evidence, not a passed live-calendar run.

That observed response also exposed a transport bug: `isError` envelopes can carry
an explicit `denied` or `blocked` result. Those states and their reason are now
preserved in the private journal, without retry. Structured account completions
are supported without pretending they have a child-process exit code; ordinary
calendar command output still requires an actual zero exit code and valid JSON.

Issue #30 remains open for live normalization acceptance, mail sending and genuine
receipt reconciliation. Issues #8/#9 still require the complete scheduled and
lifecycle tests. This adapter does not establish those outcomes by itself.
