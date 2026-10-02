# Food bank: isolated mailbox acceptance laboratory

Refs #58. Run `python scripts/adoption_lab.py --issue 58 --report /new/private/report.json`
from the repository root with Python 3.11 or newer. Reports refuse overwrites and
are created with private permissions. The full unittest suite also runs these cases.

The HTTP service binds only to loopback on an ephemeral port. Every account and
destination uses example.invalid. Per-participant credentials determine the inbound
principal independently of the claimed sender; the real NativeApplePIM HTTP client,
ApplePIMIntake identity binding and domain dispatcher consume those messages.
The service encodes the Apple PIM response contract for testing. Its DKIM-shaped
fields represent credential checks inside this fictional protocol, never real DKIM.
It does not invoke Mail.app, SMTP, Apple calendars or the user's gateway.

One capacity-limited packing shift rejects an incorrect role and an opted-out helper,
offers Alex the slot and waitlists Sam. A credential-authenticated Pat message claiming
to be Alex cannot decline it. Alex's own decline promotes Sam; repeated intake is
rejected. Only Sam's explicit acceptance confirms capacity. Local HTTP acceptance
of an offer neither proves email delivery nor confirms attendance.

SQLite acceptance records bind operation IDs to payload hashes. Repeat sends return
one receipt, changed payloads under the same ID fail, and reconciliation reads the
same record. Domain claims prevent a second outbound attempt. Only receipt references,
counts and asserted outcomes appear in the report; credentials, raw inbound messages
and transport headers are excluded. Temporary test state is cleaned on exit.

Observed local results: two notices accepted, one confirmed slot, two ineligible
signups refused, one forged decline refused and one repeated decline refused.
Independent checks reject invalid credentials and any real destination and prove
local receipt deduplication/reconciliation.

This adds a reproducible integration harness beyond the earlier grouped unit checks.
Issue #58 remains open for an authorized real test mailbox and genuine same-path
identity and delivery evidence. The installed Apple PIM bridge's missing message
binding and send receipt capabilities remain documented in #29 and #31.
