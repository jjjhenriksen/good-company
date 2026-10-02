# Google reply confirmation through the existing Latch connection

The Google adapter already sends real email and reconciles accepted Gmail receipts.
This addition supplies `GoogleReplyProvider.verified_reply` and an owner-only
`good-company-intake` command using that same Google/Latch transport. It does not
replace the mailbox connection or change Latch's approval policy.

An owner explicitly selects an enrolled, permitted recipient and a fixed command:
`STOP`, `DECLINE <assignment-id>`, `COMPLETE <assignment-id>`,
`SIGNUP <task-id>`, `ACCEPT <task-id>` or `DECLINE-OFFER <task-id>`.
The existing Google sender emails that mailbox a random 256-bit code. Only an
accepted provider receipt activates it. The participant confirms that specific
action by replying with exactly `GCVERIFY <code>` as the plain-text body, without
quoted history or a signature. Apple Mail's sole quoted `> GCVERIFY <code>` line
is also accepted. Codes expire after one hour and must not be forwarded.

The authenticated organization's inbox is read by exact opaque Gmail message ID
using `plow-gog gmail get ID --account ADDRESS --format raw --json`. The adapter
parses the documented raw-message envelope and strips only Latch's exact untrusted
data wrapper. It requires an INBOX label, exact message ID, one From address and one
nonattachment plain-text part. It performs fresh account and message observations;
calendar-cycle caches cannot supply security rechecks. HTML and attachments never
supply commands. Ambiguous MIME, message changes and unsupported commands fail closed.

The code hash must match an active challenge for the same account and enrolled
sender. The stored command, rather than additional mail text, determines the action.
A transactional claim consumes the code before domain handling. The shared intake
dispatcher then checks the roster, target ownership and signup eligibility and
records the opaque evidence reference. Replaying the code under a new message ID
or concurrently sending two copies cannot apply a second mutation. A domain rejection
or interruption requires owner review and, where appropriate, a new issuance.

This verifies possession of the enrolled mailbox's secret, not DKIM, legal identity,
exclusive mailbox ownership or the authenticity of an ordinary From header.
Forwarding the code or sharing access to that mailbox transfers that capability.
An unverified inbound email never automatically triggers a verification email.
Free-form contact-preference edits are not supported by this command grammar.

Issuance obeys standing remit, unique roster mapping, consent, recipient preferences,
organization and participant quiet hours, cadence and the shared daily communication
budget. It claims before dispatch; repeat operation IDs do not send another code.
Unknown sends remain inactive until their original operation reconciles. Previously
issued STOP confirmations remain usable while sending is paused. Issuance is blocked
when paused or unattended permission has not been attested.

## Owner command

Use the existing cycle configuration fields: `db`, `journal`, `account`, `scopes`,
`send_authority` and `unattended`, with separate private state and operation-journal
paths. Credentials come from the existing Latch environment, never configuration.
The account and organizational sender must match. Latch independently reviews every
provider invocation; a denial stays a denial.

```sh
good-company-intake --config /private/organization/cycle.json issue \
  --recipient alex@example.invalid --command 'SIGNUP packing:one' \
  --operation-id owner-request-001 --authority 'Owner approved this confirmation'
good-company-intake --config /private/organization/cycle.json reconcile \
  --operation-id owner-request-001
good-company-intake --config /private/organization/cycle.json receive \
  --message-id GMAIL_HEX_MESSAGE_ID
```

These addresses and IDs are placeholders. Only use actual recipients and actions
the owner has authorized. The command never returns the code. Its challenge ledger
stores hashes, bindings, expiry, status and receipt references. The coordination
audit retains opaque evidence. The separate existing private Latch operation journal
can retain raw mail, command bodies and codes; it must never be published or treated
as a content-free report. Expiry invalidates a code but does not erase stored private
journals or backups. Ordinary owner retention policies still apply.

## Evidence boundary

Fictional gog v0.36 response envelopes traverse the actual Google sender, reply
adapter and domain dispatcher in the regression suite. Tests cover forged headers,
another participant's code, altered commands, expiry, inbox/account races, MIME
ambiguity, unknown/denied sends, reconciliation without redispatch, ownership,
paused STOP, shared budget/cadence, signup/acceptance, restart and concurrency.
They send no external email and do not establish live Gmail acceptance.

On October 1, Latch's historical audit confirmed the Bethel 337 Gmail account had
been connected and used for real sends on September 26. During current inspection,
automatic approval review denied account enumeration because it could expose
credential information outside its configured remit. No policy was changed.
Genuine and forged messages still need controlled acceptance through this adapter
with an explicitly authorized mailbox/recipient and provider permission. Issues
#29 and #41 remain open for that evidence; merging this implementation does not
claim it happened.

Transport references: [Gmail messages.get](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get),
[Gmail raw message resource](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages),
and [gog v0.36 raw-message projection](https://github.com/openclaw/gogcli/blob/v0.36.0/internal/cmd/gmail_get.go).
# Live connector follow-up

[Apple Mail acceptance](29-41-apple-mail-live.md) now supplies real identity and
signup/acceptance/decline evidence through `GmailConnectorReplies`, the independent
Gmail plugin binding. Its scoped profile/raw MIME tools reuse the same confirmation
parser and shared dispatcher. Bethel/Latch rollout remains outside this proof.
