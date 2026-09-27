# Second provider decision (#31)

Decision: no-go for implementation until a pilot selects an authoritative calendar
and mail system. No concrete second-provider need is supplied in the current issue
or fictional examples. Google/Latch discovery and bounded owner-loopback delivery now work. General
provider normalization, external reply identity and unattended execution remain
unverified, so portability is not yet established. Do not select a vendor
on the assumption that generic nonprofit workflows imply a Microsoft tenant.

The pilot record must name its actual system/account owner, calendar scope,
unattended send permissions, recurrence/completeness behavior, verified inbound
identity and receipt reconciliation. Map these to providers.Account, CalendarPage,
SendResult and verified_reply. Reuse domain logic and the contract suite. Explicitly
mark unsupported idempotency, reconciliation or inbound verification; an ICS export
or SMTP acceptance alone is not bidirectional calendar/mail integration.

Once the need is evidenced, create one bounded adapter implementation with the same
complete-pagination, sender/scope, failure/unknown and replay tests, then prove the
same live cycle with an authorized test inbox. No integration was invented or
account credentials requested by this decision record.
