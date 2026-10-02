# Good Company issue work and evidence — October 1, 2026

The owner requested PRs for all remaining issues, selected Apple PIM for a local
instance, and authorized merging when ready. The owner separately confirmed fresh-user
installation with one-click installation allowed; #16 remains accepted on that basis.

## Provider and participant integration

| Issue | Implemented PR | Evidence and remaining acceptance |
| --- | --- | --- |
| #29 | [#212](https://github.com/jjjhenriksen/good-company/pull/212): exact-message Apple PIM identity bridge | [Mailbox/account, content/header/policy binding and spoof/race checks](29-apple-pim-replies.md). Native legacy auth results omit messageBinding; genuine and spoofed native messages still need acceptance. |
| #31 | [#213](https://github.com/jjjhenriksen/good-company/pull/213): bounded Apple PIM provider | [Exact calendars, sentinel completeness, recurring/all-day evidence and private availability](31-apple-pim-provider.md). Unsupported native occurrence/date evidence and send receipt/reconciliation are refused. |
| #41 | [#214](https://github.com/jjjhenriksen/good-company/pull/214): shared verified intake | [Signup, acceptance, decline and ordinary replies share one replay journal](41-provider-intake.md). Offers reserve capacity without confirming attendance. Native same-path acceptance depends on #29. |

The native read client has successfully read the isolated gateway. The installed
plugin's missing evidence is explicit; local simulated identity never repairs that
production gap by assertion. Runtime modules are included in the exact Docker context.

The existing Google/Latch mail connection now also has a [mailbox possession
confirmation path](29-google-mailbox-proof.md) for #29 and #41. Its owner-issued,
action-bound codes use the real sender and receipt reconciliation, and the Google
adapter feeds the shared dispatcher. Fictional transport tests cover spoofing,
expiry, replay, concurrency and state changes. Controlled live acceptance remains
outstanding; an October 1 account-enumeration attempt was denied by Latch review.

## Optional module discovery

Existing Bethel 337 fundraising work provides a concrete candidate context, not
permission to infer resource ownership, medical needs or a donor system.

| Issue | Scope PR | Decision |
| --- | --- | --- |
| #46 | [#215](https://github.com/jjjhenriksen/good-company/pull/215), [resource booking](../pilots/46-resource-booking.md) | No-go: product stock/sales do not establish bookable equipment or a reservation ledger. |
| #47 | [#216](https://github.com/jjjhenriksen/good-company/pull/216), [accessibility requests](../pilots/47-accessibility-requests.md) | Disabled candidate workflow; actual intake, fulfillment owner, consent and retention remain to be supplied. |
| #48 | [#217](https://github.com/jjjhenriksen/good-company/pull/217), [form checklists](../pilots/48-form-checklists.md) | Status-only proposal grounded in official form sources; actual required items, dates and custodian remain unconfirmed. |
| #49 | [#218](https://github.com/jjjhenriksen/good-company/pull/218), [donor/beneficiary](../pilots/49-donor-beneficiary.md) | No-go: retail fundraising and external philanthropic affiliation do not establish donor CRM or case authority. |

Each brief specifies minimal data, access/retention boundaries and observable gates.
No speculative runtime implementation issues were opened. Discovery issues remain
open where actual pilot facts are missing; merging a proposal does not enable it.

## Complete isolated adoption scenarios

| Issue | Scenario PR | Asserted outcomes |
| --- | --- | --- |
| #58 | [#219](https://github.com/jjjhenriksen/good-company/pull/219), [food bank](58-food-bank-lab.md) | Ineligible and forged signups/declines refused; qualified replacement offered and explicitly confirmed; two local notices; replay/send deduplication. |
| #59 | [#220](https://github.com/jjjhenriksen/good-company/pull/220), [arts](59-arts-change-lab.md) | Separate programs, controlled rehearsal cancellation, linked-task retirement, original receipts preserved, two private corrections and no cross-team leakage. |
| #60 | [#221](https://github.com/jjjhenriksen/good-company/pull/221), [mutual aid](60-mutual-aid-lab.md) | Verified STOP blocks both queued workflows; unaffected notices continue; consent and shared daily budget survive reopening state. |
| #61 | [board scenario](61-board-meeting-lab.md) | Online reminder without dress rules; private calendar conflict response hides title/location; exact scope and repeat-send refusal. |

Run `python scripts/adoption_lab.py --report /new/private/report.json` with Python
3.11 or newer from the repository root. Select one issue with `--issue NUMBER`.
Nine scenario/service checks exercise the NativeApplePIM HTTP client and the actual
domain code against a private loopback server with independent participant credentials,
example.invalid recipients and persisted local receipt hashes. The report retains
asserted counts and outcomes, excludes credentials/content, refuses overwrites and
explicitly marks live provider acceptance false. CI runs the same harness.

These are complete local scenarios, not genuine email delivery or native DKIM proof.
All seven integration/adoption issues retain their external acceptance requirements.
No personal calendars were modified and no external mail was sent.

The earlier `scripts/local_acceptance.py` still supplies 31 grouped library checks
and the issue inventory. The [native Apple PIM harness](local-apple-pim.md) separately
checks isolated plugin startup, guarded reads, mutation/scope denials and restart
persistence. Keep each evidence kind distinct.

## Previously completed work

PRs #204–209 fixed issues #199–203 and added the original local acceptance harness.
PR #210 added automated native Apple PIM checks. PR #211 records owner-confirmed
installation acceptance for #16. Those installation records remain valid within
[their stated evidence boundaries](16-fresh-install.md).
