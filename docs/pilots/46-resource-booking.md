# Resource booking: Bethel 337 discovery decision

Refs #46. Decision: **no-go for booking in the current fundraising pilot**.
This is a scope assessment, not an enabled module.

## Evidence and ownership

The owner's existing Bethel 337 fundraising dashboard project describes a manually
maintained workbook for product stock, vendor costs, sales, campaign revenue and
reordering. That is a retail inventory workflow. It does not establish lendable
equipment, resource custodians, reservation rights, or a shared availability source.
Apple PIM supplies event dates; a calendar entry does not confer resource ownership.
No private workbook or participant records are included in this repository.

| Requirement | Current evidence | Result |
| --- | --- | --- |
| Inventory | Fundraising product stock and remaining quantities | Cannot represent bookable equipment |
| Ownership | No designated equipment custodian supplied | Cannot authorize bookings |
| Availability | Manual stock updates; no reservation ledger supplied | Cannot infer availability from calendar silence |
| Conflicts | No capacity, overlap or setup/teardown policy supplied | Cannot resolve booking conflicts |
| Cancellation | No return, release or fee rules supplied | Cannot make cancellation commitments |

## Bounded candidate if a real need emerges

Limit a later pilot to one named shared resource, one custodian and one authoritative
reservation ledger. A request would contain event ID, resource ID, start/end with
timezone, quantity, requester ID and an opaque authorization reference. The ledger
must acknowledge a reservation before Good Company can say it is booked.
Overlapping intervals include owner-supplied setup/teardown buffers. Cancellation
must receive a ledger release receipt; an unanswered cancellation remains pending.

The custodian alone approves holds, reservations, conflict overrides and releases.
Requesters see their own status; other volunteers see no requester details.
Keep pending requests only through the event and owner-defined reconciliation
period; choose an actual retention period before enabling the module.
Stock adjustments, payments, invoices and asset disposal remain with their existing
authorities. The candidate does not write to the fundraising workbook.

## Observable acceptance before implementation

1. Supply a resource record, custodian authority and ledger interface.
2. Submit simultaneous overlapping requests: at most the ledger's declared capacity
   is reserved; a rejected request creates no local confirmed booking.
3. Exercise a stale availability read and a lost response; reconcile the same request
   ID without creating a second hold.
4. Release a confirmed booking and prove the ledger's capacity becomes available.
5. Reject an unauthorized requester and a calendar-only claim of ownership.

No implementation issues are created from an unsupported equipment requirement.
The discovery issue remains linked so an owner can supply actual resource evidence
and revise this decision without enabling a speculative booking system.
