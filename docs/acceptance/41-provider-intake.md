# Verified participant intake

`ApplePIMIntake` extends the exact-message identity bridge with `SIGNUP <task-id>`,
`ACCEPT <task-id>` and `DECLINE-OFFER <task-id>`. `dispatch` resolves one verified
message, checks the account before and after its read, and routes the bound result
to existing reply or signup domain handling. It checks mailbox remit before reading
participant content. Sending can be paused while verified STOP remains available.

A shared private `inbound_intake` journal claims an account/message exactly once
across both routes. Reusing a consumed message as a different command is rejected.
Claims precede domain mutation; a crash or unexpected failure leaves a claimed or
uncertain record for owner review rather than replaying an operation that may have
committed. Rejected domain operations also remain recorded. Only opaque identity
evidence is stored, never raw mail bodies or headers.

The integration tests send fictional native records through the actual identity
bridge and domain dispatcher, covering offers, waitlists, confirmed acceptance,
replacement, mailbox changes, pause behavior and concurrent duplicate intake. An
offer stays reserved until verified acceptance, and neither state asserts attendance.

The [Google mailbox confirmation adapter](29-google-mailbox-proof.md) now uses
this same dispatcher for preselected actions, authenticated through single-use
secrets delivered by the existing Google sender. Its tests exercise fictional
Google envelopes and preserve the same signup/offer/acceptance distinction.

Native message binding or controlled Google confirmation acceptance remains required by #29.
The [live Apple Mail/connected Gmail follow-up](29-41-apple-mail-live.md) now
records genuine signup, acceptance and decline through this shared dispatcher,
alongside rejected identity and replay attempts. Native Apple PIM acceptance
remains separate from this independently authorized Gmail route.
