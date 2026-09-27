# Scheduled delivery acceptance (#8)

Status: passed for the owner-approved isolated fictional self-test on
2026-09-27 UTC. See [`scheduled-live.json`](../../eval/providers/scheduled-live.json).
One real scheduled command ran two real-clock cycles through the deployed Google
adapter. The first dispatched an event reminder and assignment notice, retaining
both as uncertain while Latch completed them. The second refreshed the calendar
and reconciled the same two operations to genuine Gmail acceptance without any
additional sends. Both resulting messages were then observed with SENT and INBOX
labels in the authenticated self-test mailbox.

The owner approved the bounded unattended test before job execution. Latch's
reviewer allowed each operation under that policy; no interactive per-send approval
was used. Exactly one temporary job was installed, then disabled. The isolated
remit was paused and original Gatekeeper instructions restored. This proves the
requested scheduled test, not general production sending authority or separate
future scheduler ticks.

Completion procedure used:
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

## Earlier live progress (before scheduled acceptance)

The owner completed Latch setup and authorized a bounded fictional self-test.
The deployed agent then performed real account/calendar reads and four self-email
sends with genuine Gmail acceptance and inbox observations. A core event reminder
and task notice were claimed before dispatch, receipted, and refused on repeat
claim. A real owner-loopback STOP reply cancelled two queued notices, rejected
replay and blocked a later correction in the isolated test roster. Original
Gatekeeper instructions were restored after exact-action exceptions; the isolated
test remit was paused. Main organization authority remained unchanged.

At that earlier stage the disconnected-device blocker was resolved, but #8 remained open:
no scheduled operational cycle or standing unattended-send remit was established.
Manual/AI-reviewed self-test delivery is not unattended scheduled delivery. See
PRs #117 and #118 for sanitized evidence and limits.

## Packaged cycle command

Both container variants install `good-company-cycle`, including its explicit Python
module path for agent tool environments that omit `PYTHONPATH`. The wheel provides
the same command. `scripts/check_cycle_image.py IMAGE` exercises an isolated paused
cycle with networking disabled and no credentials; the image workflow runs this
check for non-publishing builds. This verifies packaging and pause behavior only,
not job installation, execution by the scheduler, or live provider delivery.
The separate live evidence above now verifies those steps for the bounded self-test.
