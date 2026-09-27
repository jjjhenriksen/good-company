# Google/Latch adapter acceptance (#30)

The implemented Google calendar/mail contract now has both automated contract
coverage and a controlled end-to-end run through the deployed Plow/Latch tools.
The acceptance evidence is split below so simulated edge cases are not presented
as live provider observations.

| Requirement | Evidence |
| --- | --- |
| Use available authorized tools | `GoogleCalendar`, `GoogleProvider`, and `LatchOperations` use the authenticated deployment MCP endpoint and actual `plow-gog` commands. No independent OAuth path is used. |
| Complete scoped recurring-instance normalization | `test_google_calendar.py` checks explicit account/scope, cursor preservation, stable moved-instance IDs, a full two-page recurring import, cancellation by absence after complete refresh, and atomic rejection of a truncated later page. These are contract fixtures. |
| Account/sender and genuine receipts | The live scheduled test authenticated the connected account, imported its exact scoped calendar, and dispatched one event and one assignment self-email. Both real message IDs were observed with SENT and INBOX labels. |
| Ambiguous result reconciliation | Both live sends initially remained uncertain. A second real-clock cycle polled their original saved operations and reconciled both, with no additional dispatch. |
| Controlled end-to-end test | One real scheduler job executed the deployed cycle command twice under owner-approved unattended authority. The job and isolated remit were disabled after the test and the original Gatekeeper policy restored. |

Live evidence: [`scheduled-live.json`](../eval/providers/scheduled-live.json),
[`google-calendar-live.json`](../eval/providers/google-calendar-live.json), and
[the scheduled acceptance record](acceptance/08-scheduled-cycle.md). Contract
checks: `test_google_calendar.py`, `test_google_mail.py`, `test_latch.py`,
`test_providers.py`, and `test_cycle.py`.

The live run contained one non-recurring event on one page and two fictional
messages sent to the connected owner account itself. Multi-page recurrence is
covered by the contract tests, not claimed as a live provider observation. This
meets #30's contract plus controlled end-to-end criteria; it does not establish
external reply identity (#29), a second provider (#31), or a production remit.
Every new deployment still needs its own authenticated account, exact calendar
scopes and explicit sending authority. Keep unattended sending disabled until
those are established; a successful test never grants wider permission.
