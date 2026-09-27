# Scheduled delivery acceptance (#8)

Status: blocked on the deployed provider connection, not on Python tests.

Observed 2026-09-26: native Plow gateway/model and installed tools work; connected
MCP discovery returns HTTP 503 after restart. Read-only inspection found zero jobs
named Good Company reminders. No operational scheduler or sending remit was
created, and no messages were sent. A connected desktop Gmail account is not proof
that the deployed runtime can use it unattended.

When the connection recovers:
1. Use the deployed provider to establish account ID, verified sender, exact calendar
   scopes and unattended-send permission. Preserve opaque evidence references only.
2. Verify an owner-controlled test inbox through that provider before adding it to
   the remit. Use one fictional event, one task and opted-in test identities.
3. Install or update exactly one Good Company reminders job in the owner context;
   retain its job ID. Record actual execution time and tool permissions.
4. Import every page of a complete calendar window, plan and allocate, then claim
   and deliver one due reminder and one assignment notice. Store actual accepted
   provider IDs or unknown status; an interrupted call is never presumed failed.
5. Repeat the same cycle and verify no additional provider sends. Keep separate
   receipts for scheduler execution, provider acceptance and inbox observation.

Required evidence: release commit/image, account/scopes attestation, scheduler job
and run IDs, two operation/receipt IDs, received-message observation, repeat-run
send count. Missing values remain missing. Never synthesize provider receipts.

## Live progress after owner authorization

The owner completed Latch setup and authorized a bounded fictional self-test.
The deployed agent then performed real account/calendar reads and four self-email
sends with genuine Gmail acceptance and inbox observations. A core event reminder
and task notice were claimed before dispatch, receipted, and refused on repeat
claim. A real owner-loopback STOP reply cancelled two queued notices, rejected
replay and blocked a later correction in the isolated test roster. Original
Gatekeeper instructions were restored after exact-action exceptions; the isolated
test remit was paused. Main organization authority remained unchanged.

This replaces the initial disconnected-device blocker, but does not complete #8:
no scheduled operational cycle or standing unattended-send remit was established.
Manual/AI-reviewed self-test delivery is not unattended scheduled delivery. See
PRs #117 and #118 for sanitized evidence and limits.
