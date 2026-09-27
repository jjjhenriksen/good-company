# Google mail adapter

`good_company.google_mail.GoogleProvider` extends the scoped calendar reader with
mail delivery and reconciliation. It uses the same authenticated Latch connection
and private durable operation journal. A trusted operator must supply a reference
to the owner's sending authority; absent that reference, sending is refused.
`unattended` defaults to false. Setting it true is an operator attestation of
observed deployment permission, not independent proof of permission. Account
listing alone never enables unattended sending. Every invocation still passes
through Latch's own permission review.

Use `Delivery(coordinator, provider)` to apply the domain's recipient, sender,
consent, quiet-hour and budget checks before claiming and dispatching a notice.
The low-level provider is a trusted integration API, not a participant endpoint.
It validates the exact sending account, recipient syntax, supported fields and
message content; it never invents addresses, attaches files, or adds HTML/tracking.
Argument values are passed literally, including bodies beginning with flag names.

## Privacy and receipts

The bundled [gog mail command](https://github.com/steipete/gogcli/blob/eaa5d631/internal/cmd/gmail_send.go)
requires a To recipient. For a BCC-only group the adapter sends separate copies,
each addressed solely to that recipient. The subject and body remain unchanged;
no new recipient is added and no other recipient address appears in that copy's
headers. Groups already having To recipients retain their To/BCC envelope.
Contact budgets still count one notice for each original recipient.

A durable group is reserved before its first child dispatch. Each child has a
unique saved Latch operation. All children must return successful command exits
with distinct actual Gmail message IDs and thread IDs before the core notice is
recorded sent. The core receipt reference contains the actual message IDs; the
private journal retains each full provider result and thread ID.

No response, nonzero exits, missing receipts and partial groups remain uncertain.
`reconcile` polls saved operations only: it never dispatches a missing child or
reissues a send. A crash before saving a handle therefore requires manual provider
evidence, not a retry. A single explicit denial/block is failed; a partly completed
group remains uncertain with the successful child evidence intact. A denial stops
dispatch of remaining children. Changing a message under the same operation ID
is rejected. No provider-level idempotency guarantee is claimed.

## Verification boundary

Tests cover core claim-to-receipt reconciliation, process restart, pending handles,
timeouts after potential sends, privacy-preserving individual copies, partial
groups, denied sends, payload changes, missing/duplicate receipts, authority
checks and literal command arguments. These use fixtures, not live delivery.

No live send was attempted for this change. The preceding account-discovery test
was denied by Gatekeeper under its current family-assistant instructions. Issue
#30 remains open for authorized live acceptance, verified inbound identities and
provider-evidence recovery when a dispatch loses its handle. Issues #8/#9 still
require the scheduled and lifecycle acceptance runs.
