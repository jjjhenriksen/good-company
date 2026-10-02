# Optional coordination workflows

The owner requested implementation of every optional module on October 1, 2026.
Each installation configures its own verified people, authoritative source,
retention and recipients. Modules start unconfigured. They are usable through the
existing agent's trusted operator tools; no additional public service is exposed.
Fictional acceptance records do not activate a real nonprofit's inventory or data.

## Configure once

`configure-module` accepts `module`, `policy`, and `authority`. Module names are
`resources`, `accessibility`, `checklists`, and `relationships`. Policy fields:

```json
{
  "enabled": true,
  "owners": ["custodian"],
  "people": {
    "custodian": {"email": "custodian@example.invalid"},
    "requester": {"email": "requester@example.invalid"}
  },
  "source": "good-company-ledger",
  "retention_days": 30,
  "notice_recipients": ["requester@example.invalid"]
}
```

People may omit email when no correspondence is permitted. Addresses must be
verified by the host, unique within this workflow, and separately authorized for
notices. General volunteer access cannot enroll someone in an optional workflow.
Actor strings and authority references are operator attestations, not identity
proof. The trusted host must bind them to verified identities. Do not expose these
CLI actions directly to participant input or the read-only evidence endpoint.

## Resource reservations

The supported authoritative system is the explicitly selected
`good-company-ledger`. It is a durable local SQLite reservation ledger. No external
inventory, payment, or external reservation API is inferred or contacted.

`add-resource` takes `resource`, `actor`, `authority`. The resource's fields are
`id`, `name`, `owner`, `capacity`, `availability` (start/end intervals with offsets),
`setup_minutes`, `teardown_minutes`. Only its named custodian can register it.
Resources are immutable; replacements use a new ID after existing reservations
are resolved. Their source and retention are selected in the module remit.

`book-resource` takes `booking`, `actor`, `authority`. Booking fields are `id`,
`resource_id`, `requester`, `start`, `end`, `quantity`, and optional `event_id`.
The requester must be explicitly enrolled. Future reservations and buffers fit
the supplied availability and the record's retention period. Capacity is checked
in the same write transaction as the reservation, using peak interval overlap.
Success returns an actual local-ledger receipt. Same-ID replay returns the
original receipt; a changed or cancelled request cannot reuse that ID.

`resource-availability` takes `resource_id`, `start`, `end`, `actor`; it is an
advisory read with no requester details. `cancel-booking` takes `booking_id`,
`actor`, `authority`; only requester/custodian can release it. Success returns a
local release receipt and immediately makes capacity available. Linking an event
captures its authorized revision. Changes require review and never silently move
a reservation or free its capacity. There are no implicit conflict overrides,
fees, stock adjustments, return inspections, or reservation claims elsewhere.

## Status, notices and retention

`module-status` takes `module`, `record_id`, `actor`. Individual records are visible
only to their recorded viewers, still enrolled in the current workflow.
`module-summary` returns aggregate counts only. `module-notice` takes `module`,
`record_id`, `recipient`, `due`, `actor`, `authority`. It queues a single-recipient
status update without private request text, document contents or identities.
Queueing/delivery does not change the record's substantive status.

`module-queue`, `module-claim` (`notice_id`), and `module-receipt` (`notice_id`,
`outcome`, `provider_id`) use the same provider `Delivery` path as other notices,
with kind `module`. The operational cycle processes these notices. Current module
and standing sender/recipient authority, record/event revision, consent, quiet
hours, contact cadence and the shared daily budget are checked before claiming.
Unknown attempts are reconciled with the original provider/account, never retried.

`expire-module-records` takes the owner's `authority`. The cycle also enforces the
configured finite retention. Expiry logically deletes personal record content and
finalized notice content, retaining ID tombstones to prevent operation replay.
In-flight/uncertain delivery evidence remains for reconciliation. SQLite free
pages and independently held backups are not securely erased.

No production CLI accepts a simulated clock. Python library clocks are used only
in fictional behavioral tests. Actual mail/calendar evidence is reported
separately from those local tests.
