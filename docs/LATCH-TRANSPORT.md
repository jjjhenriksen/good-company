# Durable connected operations

`good_company.latch` supplies authenticated MCP transport and a durable command
journal for the Google adapter and scheduled delivery work (#30, #8, #9).
Use the deployed `PLOW_API_BASE` and `PLOW_AGENT_TOKEN`; do not establish a separate
Google OAuth session. Read Latch's current `google-workspace` skill before using
Google commands. Its current command entry point is `plow-gog`, not `gog`.

`LatchOperations.execute(operation_id, argv, goal)` commits a unique operation
and payload fingerprint **before** dispatch. Reusing the operation returns its
saved state; changed arguments are rejected. `poll(operation_id)` checks only the
saved pending-result or running-command handle. A new process can reopen the same
database and continue polling. The journal belongs in the private durable state
directory, alongside the application database: returned content can contain
private mail/calendar data and must not enter published acceptance artifacts.

Transport failures during dispatch remain uncertain. A crash in the gap between
dispatch and saving the handle also remains uncertain. Neither case is resent.
Observation failures retain the existing handle. Denied, blocked, expired and
unknown outcomes do not trigger replacement commands. Pass an operation's blocked
diagnosis back to the owner; this module does not change permissions or approvals.
HTTP redirects are refused, credentials are held only in memory, and transport
exceptions expose a fixed error code rather than a response body.

For a pending request that returns a running command, the journal switches to the
job handle and `plow_get_output`. If that tool is unavailable, the operation stays
running/unresolved; callers must not re-dispatch it. A zero exit code only means
the command succeeded. A mail adapter must still validate a genuine provider
receipt before recording a send. This transport does not assert sender identity,
calendar completeness, unattended permission, or message delivery on its own.

## Observed validation, 2026-09-26

The candidate module was loaded separately in the existing deployed container;
the installed package and main organization state were unchanged. Through the
authenticated Latch connection, `plow-gog calendar events --help` completed with
exit code 0. A second process reopened the journal and returned that completed
result with zero new dispatches. No mail was sent or calendar data changed.

The legacy `gog` spelling was rejected by the current tool boundary. Its original
operation remains uncertain rather than being silently rewritten or retried.
The corrected read-only documentation probe used a distinct operation ID.

Regression coverage includes restart recovery, observation timeouts, uncertain
dispatch, changed payload rejection, shared-journal dispatch suppression, nested
pending-to-running handles, terminal denial states, malformed results and stale
poll results arriving after completion. Pending/running recovery tests use
fixtures; the live probe completed immediately and does not prove delayed mail
delivery. This is infrastructure toward #8/#9/#30, not their acceptance closure.
