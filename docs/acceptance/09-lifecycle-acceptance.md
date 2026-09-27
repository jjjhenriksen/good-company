# Live lifecycle matrix (#9)

Status: passed for the owner-controlled fictional lifecycle scope. The September 26 owner-approved run on source
`3c526d916f2f066f32aab8e8d0fe15bef81b4991` verified two real self-emails,
owner-loopback decline/completion handling, a real calendar location change, and cancellation/restoration of the same event.
[Sanitized results](../../eval/providers/lifecycle-live.json) retain receipt
hashes and distinguish live observations from controlled fixtures. Issue #9 is complete within this authorized scope; #29 remains open for general
external sender identity.

| Case | Observed result | Evidence boundary |
| --- | --- | --- |
| Pause before delivery | Delivery refused; provider send method called zero times | Isolated deployed ledger and instrumented provider guard |
| Pause after an attempt | Reconciled while paused, preserved the sent payload/receipt, refused a new send | Simulated lost final acknowledgement in a clone of the real scheduled-send ledger; actual stored Google receipt, no new network operation |
| Source change before delivery | Complete live refresh superseded the pending notice; replacement payload used the new location and retained the provider citation | Real Google event update and refresh; no replacement email sent |
| Source change after delivery | Original sent payload and receipt remained exact; no new routine notice; explicit correction review required | Clone of the earlier genuinely receipted ledger plus the same live changed snapshot |
| Decline | Actual self-email appeared in SENT and INBOX; assignment declined, task stayed open, pending notices cancelled | Exact message/thread matched an owner-authorized send receipt; separate isolated ledger |
| Completion | Actual self-email appeared in SENT and INBOX; task completed, pending notices cancelled | Exact message/thread matched an owner-authorized send receipt; separate isolated ledger |
| Replay and spoof | Each reply applied once; replay and unauthenticated fixture input refused without assignment, task, notice, consent or audit changes | Spoof is a controlled provider fixture; this does not establish authentication of arbitrary external senders |
| Ambiguous provider result | Earlier scheduled run recorded two uncertain sends, then reconciled both without another send | [Genuine scheduler evidence](../../eval/providers/scheduled-live.json), two real inbox receipts |
| Cancellation before/after delivery | Complete live refresh returned zero events; pending notice superseded and claim refused; prior sent payload/receipt preserved with no replacement routine notice | Exact fixture deleted into Google Calendar Trash; deployed adapter independently observed cancellation; both isolated ledgers added zero sends |
| Restoration | Same event restored from Trash; complete refresh returned it with empty location; raw read matched original identity, status, times, attendees, privacy, reminders, title and description | Normal owner-authenticated UI recovery, followed by independent provider readback |

All eight lifecycle ledgers are paused. Exactly two new self-emails were sent,
with no attachments or external recipients. Gatekeeper remained enabled and its
original instructions were restored. No extra reminder or correction was sent.

## Calendar cleanup completed

The fictional event originally had no location. The provider's documented
`--location=` clear command returned exit 0 but preserved the temporary room.
The [pinned upstream implementation](https://github.com/openclaw/gogcli/blob/v0.36.0/internal/cmd/calendar_update_patch_plan.go#L105)
sets an empty `Location` without adding it to `ForceSendFields`, consistent with
that observed failure. The original partial report correctly left cleanup open.

After the owner supplied the authenticated Google Calendar window, its normal
editor cleared the location. A fresh provider snapshot confirmed the empty value.
The exact fixture was then deleted into recoverable Trash, a complete provider
snapshot confirmed its absence, and the before/after-delivery cancellation checks
ran against isolated ledgers. Restoring that exact Trash entry returned the same
provider event ID. A final complete snapshot and raw read independently verified
the original location, status, dates/times, guest list, visibility, transparency,
organizer, creator, reminders, iCalUID, title and description. The fixture is
restored; no invitations or additional emails were sent.

An initial cancellation observation raced the UI change and still returned the
event. Only the subsequent complete zero-event snapshot, after Calendar showed
“Event deleted” and the exact Trash entry, counts as cancellation evidence.

The relay also intermittently reported HTTP 503/device disconnected while the
app displayed Connected. Restarting the official Latch app restored enough
connectivity to complete the changed snapshot, clear attempt and readback.
Connection initialization was retried before dispatch; durable operation IDs
prevented repeating emails or uncertain mutations.
