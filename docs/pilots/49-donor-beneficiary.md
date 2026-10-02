# Donor and beneficiary integration: Bethel 337 assessment

Refs #49. The owner subsequently requested all optional workflows. The selected
[implemented pilot](../OPTIONAL-WORKFLOWS.md#donor-and-beneficiary-follow-up) uses a
private owner-held JSON register for read-only source observations and separately
consented follow-up. This is a go for that bounded local workflow. The earlier
assessment below remains the boundary for actual Bethel CRM/case data; no such
system, donor roster, beneficiary record, payment or case authority is inferred.

The existing fundraising dashboard describes product sales, vendor expenses, stock
and campaign revenue. Retail purchasers are not automatically donors, and a campaign
total is not a beneficiary record. No donor CRM, authorized ledger integration,
beneficiary intake or consent source has been supplied.

[The HIKE Fund](https://thehikefund.org/) is JDI's philanthropic project and has its own
external authority. That relationship does not give Good Company permission to read
grant applications, contact recipients or manage cases. Do not infer a local donor
system or beneficiary identity from the affiliation.

## Concrete alternative considered

A later owner-authorized pilot could remind a campaign coordinator to record an
aggregate fundraising transfer in the existing authoritative ledger. Minimum fields:
campaign ID, reporting period, aggregate amount/currency, source ledger reference,
responsible coordinator and acknowledgment reference. This is an aggregate reporting
aid; it would exclude individual donor/recipient names and payment credentials.
The current workbook description does not prove a donation-transfer ledger, so even
this alternative remains disabled pending a named source and authority.

| Boundary | Required evidence before a future pilot | Current outcome |
| --- | --- | --- |
| Workflow | Named reporting action and responsible owner | Product sales known; donation action unconfirmed |
| System | Exact authoritative ledger and read/write scope | No authorized connector supplied |
| Consent/access | Separate permission for donor or beneficiary data | None supplied |
| Retention | Purpose and deletion period for each minimal field | Must be selected before enabling |
| Receipt | Ledger acknowledgment of a reporting action | A sent reminder is insufficient |

## Access and exclusions

Volunteer rosters and opt-in do not authorize donor or beneficiary processing.
Keep any future reporting permission separate. Only the named finance/reporting owner
could acknowledge ledger status. Use aggregates in ordinary coordination messages;
never attach applications, medical records, income details or a donor list.

No payments, tax receipts, donation promises, eligibility determinations, case
management, grant approval, recipient outreach or transfer of beneficiary records
are implemented by this proposal.

## Decision and future acceptance gate

Do not create speculative CRM implementation issues. Reopen the assessment when
the owner identifies a specific workflow, authoritative system, separate access/consent,
retention period and observable receipt. A bounded future test must reject a sales
record misclassified as a donation, prevent recipient-data access from volunteer
authority, reconcile an uncertain ledger update without duplication, and avoid
claiming a transfer based on an email notification. Public source review: 2026-10-01.
