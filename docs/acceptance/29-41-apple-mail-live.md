# Live Apple Mail and Gmail identity/signup acceptance — October 1, 2026

The owner explicitly authorized Apple Mail test emails. Native `mail-cli send`
used the owner's Main and Official Gmail accounts; no other people were contacted.
The existing authenticated Gmail connector supplied its actual profile, accepted
send IDs and original base64url RFC 2822 message resources. Good Company used
isolated synthetic organization/roster/task state and the production
`GmailConnectorReplies` adapter plus the shared `intake.dispatch` domain path.
No identity assertion, mailbox copy, raw message or provider result was synthesized.

## Observed outcomes

The [content-free proof manifest](apple-mail-live-proof.json) contains 15 passing
assertions with receipt/message hashes and the private original report's digest.
It records these real-message outcomes:

- An ordinary Apple Mail STOP without a code was refused; consent stayed enabled.
- The other owner-controlled mailbox returned the enrolled participant's valid
  code and was refused; capacity stayed unchanged. This exercises an unauthorized
  identity/command attempt, not a forged SMTP From or DKIM header.
- A genuine signup reserved one offer without asserting attendance.
- Returning the consumed code under a different Gmail message ID was refused.
- Genuine acceptance confirmed exactly one owned slot.
- Genuine decline released that slot and reopened capacity.
- Three accepted confirmation sends activated the corresponding codes. The
  shared dispatcher retained actual applied signup/acceptance/decline records.

The independent mailbox-possession verifier was exercised by both accepted and
rejected real messages through this same adapter. Original message content was
parsed unchanged, with fresh account/message observations, rather than fabricated
from snippets or inferred from a display name. Existing domain tests additionally
cover assignment ownership, completion, preferences, waitlists, concurrency and
paused STOP handling.

## Compatibility correction and limits

Apple Mail emitted a newly composed confirmation as one quoted plain-text line
inside multipart/alternative. The parser now accepts a sole `> GCVERIFY <code>`
line as well as the unquoted form. Multiple lines, quoted history, extra commands,
ambiguous MIME, HTML-only content and ordinary sender/authentication headers still
cannot authorize a mutation. A delivered secret remains necessary.

Supplemental live completion and paused-STOP tests were deferred when issuance
reached the configured 9 p.m. organization quiet hours. The adapter refused that
new send. These outcomes are **not** claimed as live successes; their library
regression tests pass. The earlier private harness failures and receipt/tombstone
state were preserved; continuation reused existing accepted challenge receipts
without redispatch, never reset consumed codes and did not change the quiet-hours rule.

This acceptance covers the independently authorized personal Gmail connector.
Bethel/Latch permission and deployment are not proven here. Latch's account-list
denial was honored; its approval policy and credentials were not changed. Apple
PIM's native DKIM/message-binding bridge and second-provider acceptance remain
separate. Mailbox possession does not establish legal identity or exclusive access;
forwarding a secret transfers that capability.

The required live identity and signup/acceptance/decline integration gates in #29
and #41 have evidence through this connector. The supplemental cases and actual
organizational rollout remain explicitly outside these completed checks.

## Host binding

`GmailConnectorJournal(path, call)` accepts a trusted host callable that invokes
the actual Gmail plugin tools and returns their MCP result envelopes.
`GmailConnectorReplies` requires an explicit mailbox, organization state and owner
send authority. `call` must be a real authenticated host binding; fixture callbacks
are never acceptance evidence. The adapter permits only `gmail_get_profile`,
`gmail_read_email` and `gmail_send_email`, reads raw MIME, and cannot read calendars.
Its fresh profile must match the selected organization sender.

Send intent and fingerprint are stored before the external call. The journal
retains an accepted real Gmail ID or an unknown outcome, never automatically
redispatches a send, and does not activate unknown challenges. Reconciliation can
return saved receipts; an unknown send without a returned ID needs owner review.
The supported `good-company-intake` CLI remains the separate Latch transport; it
does not silently switch connector accounts or inherit permission from this binding.
