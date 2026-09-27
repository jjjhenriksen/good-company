# Donor/beneficiary integration decision (#49)

Decision: no-go without a concrete pilot workflow and authoritative external system.
Volunteer coordination does not authorize donor processing, beneficiary casework or
copying sensitive records. No CRM, payment or case-management capability is added.

A pilot must identify the specific operation (for example a read-only aggregate
program count), system of record, owner, minimum fields, consent/legal basis as
provided by that organization, role restrictions, retention and deletion process,
and evidence of the operation's success. Keep these decisions separate from
volunteer roster authority; do not inherit broad access automatically.

Prefer a bounded read-only/aggregate integration when it meets the supplied need.
Exclude charging/refunds, payment-card data, eligibility determinations, case notes,
health records and benefit promises unless separately specified and reviewed.
Only create implementation issues after a documented go decision states the exact
API action, access boundary, data lifecycle and observable acceptance test.
