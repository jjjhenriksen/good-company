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

## Accessibility arrangements

Configure `accessibility` with the named event-service desk as its source and a
workflow-specific coordinator, requester and service owner. `request-accessibility`
takes `request`, `actor`, `authority`. Request fields: `id`, `event_id` (the engine's
normalized event ID returned by `events`), `requester`, `owner`, `service_owner`,
`arrangement`, `consent`, `share_with`. The consent reference attests to sharing
with exactly the named coordinator/service owner and the configured retention.
Only a verified requester may submit their request. Request text describes the
arrangement; diagnoses, medical records and proof of disability are not fields.

`update-accessibility` takes `request_id`, `action`, `actor`, `evidence`, `authority`.
The responsible coordinator acknowledges a requested arrangement (`acknowledge`),
the service owner confirms it (`arrange`), and the coordinator records evidence
of an actual separate check (`verify`). No receipt for a sent email changes these
states. `unavailable` records an evidenced inability; it removes previous
confirmation/check evidence. `recheck` captures the current event revision and
returns to acknowledged, requiring fresh service confirmation and verification.
Changed/cancelled events expose `needs_review`, never an outdated verified claim.
`withdraw` is restricted to the requester, removes the arrangement/consent text,
revokes the service owner's view and invalidates pending notices. Withdrawal
cannot be undone by replay; renewed consent uses a new request ID.

Only the consented viewers can retrieve the record. Status messages omit the
requested arrangement. Confirmation/check references are trusted-host attestations
from the responsible people's real observations; fictional tests demonstrate the
state machine without asserting an actual accommodation exists.

## Document checklists

Configure `checklists` with the exact authoritative status source, assigned
custodian, separately consented people, retention and reminder recipients.
`add-checklist` takes `item`, `actor`, `authority`. Fields: `id`, `title`, `subject`,
`owner`, `form_url` (official HTTPS link), `form_version`, `due` (actual supplied
date/time with offset), `source`, `consent`, optional normalized `event_id`.
The assigned custodian registers the requirement. No form contents, signatures,
medical records, registry credentials or background-check findings are stored.

`update-checklist` takes `item_id`, `action`, `actor`, `evidence`, `authority`:
the participant can `report-submitted` or `withdraw`; the assigned custodian can
`acknowledge` an actual source observation, `mark-missing`, `change-deadline`
(with `due`), `replace-version` (with `form_version`), or `recheck-event` after a
linked event changes. New versions/event rechecks clear old acknowledgments.
Reported submission never becomes source acknowledgment automatically, and
acknowledgment never claims certification/compliance. Repeated identical source
updates preserve the revision. Changed requirements invalidate pending notices.

`plan-module-notices` and the cycle queue at most one private reminder per current
missing-item revision when its supplied deadline is within one day or overdue.
The configured recipient/consent/quiet-hour/budget rules still apply. The reminder
includes the current title, deadline and official form link, with no form contents.
Reported-submitted, acknowledged and withdrawn items receive no automatic missing
reminder. Manual status correspondence also uses the bounded module notice path.
There is no inferred deadline, form submission, attachment upload or verification.

## Donor and beneficiary follow-up

Configure `relationships` with the exact owner-selected authoritative register,
separate people/owners, explicit notice recipients and finite retention. The built
integration reads an owner-held private JSON register. It has no network discovery,
source writes, payment execution, tax receipt, grant approval, eligibility decision,
case notes or medical/income data. A real CRM connector is separately selected;
the register import is not a live CRM subscription or inferred Bethel integration.

`add-relationship` takes `record`, `actor`, `authority`. Fields: `id`, `kind`
(`donor` or `beneficiary`), `subject`, `owner`, `external_id`, `source`, `purpose`,
`consent`. Only the assigned owner registers an independently consented person.
An active external record cannot be bound twice. A roster entry or retail sale
is insufficient. Only the person and assigned owner can retrieve its status.

`sync-relationship` takes `record_id`, `snapshot`, `actor`, `authority`. Snapshot
fields: `source`, `external_id`, `kind`, `state`, `version`, `checked_at`, `evidence`.
Donor states are `pledged` and `recorded`; beneficiary states are `requested` and
`confirmed`. These produce source-observed local statuses, never an assertion that
Good Company processed money or delivered a service. Donor observations optionally
include `amount_minor` and a supplied uppercase three-letter `currency` together;
amounts are integers, not inferred totals. A fresh observation must match the exact
source/person/kind binding. Same-version replay preserves the original revision;
conflicting or superseded versions are rejected. Evidence is a verified-host
attestation to the actual register observation, not a new authentication mechanism.

`import-relationship-register` takes `path`, `actor`, `authority`. Supply an
owner-held regular file with permissions 0600, at most 2 MB and 1000 entries:

```json
{
  "source": "owner-selected-register",
  "complete": true,
  "records": [{"record_id": "bound-local-id", "snapshot": {
    "source": "owner-selected-register", "external_id": "opaque-source-id",
    "kind": "donor", "state": "recorded", "version": "source-version",
    "checked_at": "2026-10-01T17:00:00Z", "evidence": "private-observation-reference"
  }}]
}
```

All rows apply atomically or none do. Observations are at most 15 minutes old;
use the actual clock, not the illustrative date above. Missing rows never remove
consent or establish an absent outcome. The input file is never modified.

`withdraw-module-record` takes `module`, `record_id`, `actor`, `authority` for
accessibility, checklists or relationships. Verified subjects can withdraw even
while the workflow is paused. Private content is removed and queued follow-up
invalidated; source imports cannot restore old consent. Resource reservations use
`cancel-booking` instead so ledger capacity and release receipts remain coherent.

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
