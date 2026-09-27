# Google/Latch adapter validation status

Issue #30 remains open. The initial HTTP 503 was a disconnected Latch device.
After installing Latch and the owner's setup, the deployed agent obtained the
actual tool catalog, verified account/calendar reads, and delivered four explicitly
authorized fictional self-emails with genuine receipts and inbox observations.
Owner-loopback STOP handling and duplicate core claim refusal passed. Temporary
Gatekeeper exceptions were removed and the isolated test remit was paused.
This is evidence for reviewed self-tests, not a complete production adapter.

The separately connected Codex Gmail account does not prove that the deployed
Plow owner session has calendar access, unattended sending permission, or receipt
lookup. Do not bypass Plow/Latch approval boundaries with independent OAuth,
or substitute synthetic receipts for a live acceptance run.

Use `scripts/provider_probe.py` with the deployment's existing environment to
repeat read-only discovery. It reports safe status codes and tool names, never
credentials, endpoint tokens, mail bodies or recipient lists. A reachable catalog
still requires mapping exact schemas into `good_company.providers`, checking
verified account identity, full scoped recurrence pagination, permissions, actual
provider receipts, and unknown-outcome lookup. A provider send must remain disabled
until those capabilities are established.

The Google calendar and mail adapters are now implemented, with durable Latch
operations and reconciliation. A later owner-approved read-only run through the
actual calendar adapter authenticated the account and imported the existing
fictional event's exact one-hour scope. Both Latch operations completed, and a
journal reopen reused them without network dispatch. See
[the calendar adapter evidence](GOOGLE-CALENDAR.md). Live multi-page/recurrence,
mail-adapter delivery/reconciliation and unattended scheduling remain outstanding;
the earlier direct self-mail receipts do not prove those adapter paths.
