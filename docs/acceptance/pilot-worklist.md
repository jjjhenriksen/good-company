# Remaining Good Company work — October 1, 2026

The owner requested work on every open issue and selected Apple PIM for a local
testing instance. No specific nonprofit pilot, inventory system, accessibility
intake, form authority or donor/beneficiary system was identified. The existing
local/hosted installation evidence remains valid within its recorded limits.

## Concrete fixes ready for review

| Issue | Change |
| --- | --- |
| #199 | Preserve empty state directories with backward-compatible backup restore (#204). |
| #200 | Use the organization's local date for source applicability/review (#205). |
| #201 | Return the matching MCP SSE result before stream EOF (#206). |
| #202 | Preserve/reconcile sparse calendar cancellations and retire stale queued work (#207). |
| #203 | Report reserved offers separately from truly unassigned staffing (#208). |

Each PR has regression coverage and its own passing Python 3.11–3.13 CI. These
issues close when their corresponding PRs merge.

## Installation and live workflow work

| Issue | Prepared or observed | Required completion evidence |
| --- | --- | --- |
| #16 | [Isolated Apple PIM startup and restart](local-apple-pim.md), paused ledger, independent private token. Existing Plow fresh/hosted evidence remains in [16-fresh-install.md](16-fresh-install.md). | Independent hosted saved-state/restart proof, fresh phone/account activation and actual Index texting installation flow. A Mac gateway does not satisfy these. |
| #29 | Existing roster/remit/ownership/replay checks pass. Apple PIM's pinned authserv/DKIM boundary is a concrete candidate. | Implement the mailbox-bound VerifiedReply bridge; genuine and spoofed messages must traverse that exact integration. Preserve opaque evidence, reject domain-only identity and unauthenticated commands. |
| #31 | Apple PIM loads and its native helper reads the explicitly scoped calendar tool. Contract gaps are [documented](local-apple-pim.md#provider-work-that-the-probe-exposed). | Stable recurring occurrence identity, demonstrably complete bounded reads, exact mailbox/account permissions and truthful receipt/reconciliation behavior. |
| #41 | Signup/capacity/waitlist/acceptance/replacement regressions pass, including simultaneous responses and opt-out. | Bind the same proven #29 identity path to signup/RSVP commands and retain same-path live evidence. Offers must remain separate from confirmed participation. |
| #58 | Five repeatable fictional food-bank checks pass. | Authorized test mailbox; real eligibility/offer/decline/replacement observations and provider references. |
| #59 | Five repeatable fictional arts-change checks pass. | Move/cancel controlled scoped events; real team-specific corrections and linked-work handling, with receipt/deduplication evidence. |
| #60 | Five repeatable fictional stop/budget checks pass. | A verified live STOP with pending event/task notices; no later send to that helper while other authorized work continues. |
| #61 | Four repeatable fictional board checks pass. No dress policy is fabricated; private conflict titles stay hidden. | Real routine scoped reminder receipt and repeat-run deduplication through an authorized mailbox. |

Run `python3 scripts/local_acceptance.py` to reproduce the grouped fictional checks.
Their successful fixture receipts are not provider receipts. Local mail remains
disabled until an exact test sender/audience is authorized.

## Optional modules: current scope decisions

These are prepared discovery briefs, not findings about an actual nonprofit.
The current decision is to defer production implementation for all four modules
until a concrete pilot supplies the source and authority below. No speculative
implementation issues were opened and none of the discovery issues is closed.

| Issue | Candidate bounded workflow | Minimal proposed data / responsible role | Evidence needed for a go decision |
| --- | --- | --- | --- |
| #46 Resources | Availability check, explicit reservation, cancellation and readback for one equipment type in one authoritative inventory. | Resource ID, time window, reservation ID, responsible coordinator; access limited to the inventory owner and authorized bookers. | Actual ownership/inventory, conflict and concurrent-reservation rules, allowed actions, cancellation/expiry semantics, retention period and authoritative booking receipt. Do not infer an equipment reservation from a calendar event. |
| #47 Accessibility | Acknowledge an opted-in request, route it to a named fulfillment owner, record verified fulfillment or an unresolved gap. | Event ID, requested practical arrangement, owner/status and consent; omit diagnoses or unrelated personal history. | Pilot intake/fulfillment process, access list, explicit consent, retention/deletion rules, escalation responsibility and evidence of actual accommodation. Message-format preferences alone do not prove accommodation. |
| #48 Forms | Sourced checklist and deadline reminders for one named form set; status from its designated authority. | Form identifier/version, due date, participant reference, authoritative completion status and evidence reference. Avoid retaining form contents when status suffices. | Supplied forms/deadlines, authoritative status source, allowed readers, retention and reminder remit. Keep document validation, legal/compliance certification and automatic collection outside this proposed scope. |
| #49 Donor/beneficiary | One explicitly named lookup/status workflow against the pilot's chosen system. | External record ID and only fields essential to that workflow; separate access/consent/retention from volunteer operations. | Specific workflow and system, ownership/access/consent, minimal fields and retention. Payment processing, beneficiary case management and inferred eligibility remain excluded until independently scoped and implemented. |

A coordinator can now review concrete boundaries and supply only the missing
pilot facts. For each approved module, create a bounded implementation issue with
its actual authoritative source, permission model, failure/cancellation behavior
and observable acceptance tests. Avoid silently broadening routine onboarding.
