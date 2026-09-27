# Live lifecycle matrix (#9)

Status: partial. The September 26 owner-approved run on source
`3c526d916f2f066f32aab8e8d0fe15bef81b4991` verified two real self-emails,
owner-loopback decline/completion handling, and a real calendar location change.
[Sanitized results](../../eval/providers/lifecycle-live.json) retain receipt
hashes and distinguish live observations from controlled fixtures. Issue #9
remains open for cancellation/restoration; #29 remains open for general external
sender identity.

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
| Cancellation before/after delivery | Not exercised live | Installed gog v0.36.0 exposes deletion but no restore/status-update command; cancellation was withheld until a recoverable path is available |

All six lifecycle ledgers are paused. Exactly two new self-emails were sent,
with no attachments or external recipients. Gatekeeper remained enabled and its
original instructions were restored. No extra reminder or correction was sent.

## Calendar cleanup still required

The fictional event originally had no location. Updating it to the fictional
room succeeded and a complete calendar refresh observed the change. The
provider's documented `--location=` clear command returned exit 0, but a fresh
raw read still contained the temporary location. Therefore cleanup is **not**
complete, and the event must not be described as restored. Its original status,
times, guest list, visibility and transparency remain unchanged.

The [pinned upstream implementation](https://github.com/openclaw/gogcli/blob/v0.36.0/internal/cmd/calendar_update_patch_plan.go#L105)
sets an empty `Location` without adding it to `ForceSendFields`, consistent with
the observed omission from the Google patch. Do not retry the same ineffective
clear command or substitute whitespace for the original empty state. Use the
owner-authenticated Google Calendar page to clear the location and read it back.
Then exercise cancellation with a verified restore path for this exact fixture.
Do not delete another event or send invitations to obtain acceptance evidence.

The relay also intermittently reported HTTP 503/device disconnected while the
app displayed Connected. Restarting the official Latch app restored enough
connectivity to complete the changed snapshot, clear attempt and readback.
Connection initialization was retried before dispatch; durable operation IDs
prevented repeating emails or uncertain mutations.
