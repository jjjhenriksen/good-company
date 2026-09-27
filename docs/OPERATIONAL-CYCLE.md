# Operational scheduler cycle

`good-company-cycle` is the owner-only entrypoint for a single bounded run of the
existing OpenClaw scheduler. It does not create a second scheduler or enable a
standing remit. It requires the durable application database, a separate private
Latch operation journal, an explicit account/scope mapping and an observed
unattended-send authority reference. Plow credentials come from the runtime
environment, never this configuration file.

Example private configuration (fictional values, not deployment authority):

```json
{
  "db": "state.sqlite",
  "journal": "latch.sqlite",
  "account": "coordinator@example.invalid",
  "scopes": {"approved-events": "exact-calendar-id"},
  "send_authority": "owner-instruction-and-observed-permission-reference",
  "unattended": false
}
```

Relative state paths resolve beside the config file. Leave `unattended` false
until the connected account's actual sending permissions have been established.
Both this configuration and the domain's enabled standing remit are required.
A boolean in a file is an operator attestation, not live acceptance evidence.

After authorization, the owner-context scheduler invokes a command of this form:

```sh
good-company-cycle --config /var/lib/good-company/private/cycle.json \
  --cycle-id 'scheduler-job:scheduled-tick' \
  --start '2026-10-03T00:00:00Z' --end '2026-10-10T00:00:00Z'
```

The scheduler supplies real window dates and a distinct cycle ID per scheduled
tick. To resume an interrupted tick, reuse its ID, window and configuration.
There is no production `--now` override. A changed account, scope mapping, remit,
profile or window cannot reuse an old cycle ID. A completed cycle returns its
recorded summary rather than repeating its delivery actions.

The cycle:

1. Takes a nonblocking process lock beside the database. Another worker reports
   `already_running`; the operating system releases the lock if a process dies.
2. Checks the standing remit and provider identity/permission. Paused operation
   performs no provider actions; the CLI refuses unverified send permission
   before establishing a connection.
3. Imports complete calendar pages for every standing scope. Any missing,
   pending, invalid or denied refresh blocks all new deliveries in that cycle.
4. Plans reminders and allocates eligible tasks using the existing domain logic.
5. Reconciles previously attempted notices using saved operations, and claims due
   approved reminders, task notices and authorized corrections before dispatch.
   Consent, quiet hours, current authority and shared budgets still apply at each
   claim. It does not auto-authorize drafts or invent corrections.
6. Saves counts without names, addresses, subjects or message bodies. Detailed
   receipts remain in the private domain and provider journals.

`completed` means the cycle finished its work, not that every message was sent.
Inspect `uncertain`, `failed`, `deferred` and `planning_exceptions`. Exit code 0
also covers paused/already-running invocations; blocked and configuration errors
return 2. Do not treat process success as delivery evidence. Provider uncertainty
never grants permission to retry a send.

## Validation boundary

Automated tests exercise successive cycles without duplicate sends, delayed
receipt reconciliation, process interruption after provider acceptance, overlapping
workers, pause, missing permission, incomplete second-calendar reads, configuration
changes and private-data-free summaries. These use fixture providers.

No operational scheduler job has been installed or enabled by this change. The
live Latch account-discovery denial and pending read-only policy exception remain
unresolved. Issue #8 requires an actual owner-context job, observed execution,
real reminder and assignment receipts, and a repeat run with no duplicate sends;
this implementation is necessary infrastructure, not that acceptance evidence.
