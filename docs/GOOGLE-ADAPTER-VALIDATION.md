# Google/Latch adapter validation status

Issue #30 remains open. On 2026-09-26 the deployed Plow credential resolved an
agent identity and connected-tool endpoint. Initializing that endpoint returned
HTTP 503. No authorized calendar/mail tool catalog could be obtained through this
path; no calendar normalization or provider send is claimed.

The separately connected Codex Gmail account does not prove that the deployed
Plow owner session has calendar access, unattended sending permission, or receipt
lookup. Do not route around the missing Plow connection with independent OAuth,
or substitute synthetic receipts for a live acceptance run.

Use `scripts/provider_probe.py` with the deployment's existing environment to
repeat read-only discovery. It reports safe status codes and tool names, never
credentials, endpoint tokens, mail bodies or recipient lists. A reachable catalog
still requires mapping exact schemas into `good_company.providers`, checking
verified account identity, full scoped recurrence pagination, permissions, actual
provider receipts, and unknown-outcome lookup. A provider send must remain disabled
until those capabilities are established.

The committed probe is diagnostic groundwork, not the completed Google adapter.
