# Optional workflows: implemented local acceptance

The owner requested all four optional workflows on October 1, 2026. The implementation
uses an explicitly selected local reservation ledger, named event service desk,
status-only document register and private read-only relationship register. Records
in acceptance are fictional. Actual Bethel inventory, requirements, arrangements
and a CRM/beneficiary system are not inferred or enabled by these tests.

Implemented PRs: [resource reservations #226](https://github.com/jjjhenriksen/good-company/pull/226),
[accessibility #228](https://github.com/jjjhenriksen/good-company/pull/228),
[checklists #230](https://github.com/jjjhenriksen/good-company/pull/230).
The donor/beneficiary implementation and combined command harness follow #231.
See [the runnable operator workflows](../OPTIONAL-WORKFLOWS.md).

## Behavior and command evidence

628 behavior tests passed on the final implementation locally. New checks include
capacity races and buffers, local reserve/release receipts, wrong actor/source/view,
service confirmation versus actual checks, changed event revisions and stale calendar
evidence, participant report versus authoritative acknowledgment, changed deadlines,
private source import atomicity/version replay, consent withdrawal while paused,
shared communication budget/quiet hours, account-bound unknown-send reconciliation,
retention after reconciliation, aggregate health, cycle processing and v1 migration.

`python3 scripts/optional_workflows_lab.py --report /new/private/report.json` runs all
four workflows through the real CLI with the actual clock and a fresh private database.
The observed report passed 15 checks: local booking receipt/replay/conflict/release;
accessibility state order, distinct confirmation/check, other-team refusal and
withdrawal; participant submission/custodian authority/acknowledgment; retail-sale
refusal and read-only register import/replay; and aggregate identity omission.
It makes no network calls, sends no external email and reports both
`live_provider_evidence: false` and `real_nonprofit_fulfillment: false`.
CI runs this harness on Python 3.11–3.13 alongside the existing nonprofit adoption lab.

## Closure boundaries

The bounded implementation issues #225, #227, #229 and #231 are separate from
the original real-pilot discovery issues #46–49. The requested software is usable
once configured with supplied people/sources/retention. Real organizational facts
and authorizations still need to be observed for the original discovery criteria.
The existing real Apple Mail/Gmail evidence for #29/#41 is unchanged. Additional
live adoption scenarios #58–61 and provider portability #31 remain their own gates;
this fictional command report is not substituted for them.
