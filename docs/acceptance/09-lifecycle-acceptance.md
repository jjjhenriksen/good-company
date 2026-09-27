# Live lifecycle matrix (#9)

Status: blocked by #8 and deployed connected-tool HTTP 503. Unit tests already
exercise state transitions; they cannot substitute for the following live results.
Use fictional records and an independently verified owner-controlled test inbox.

| Case | Before provider attempt | After provider attempt | Required observation |
| --- | --- | --- | --- |
| Pause | Claim refuses paused authority | Reconcile in-flight receipt | No new attempt after pause |
| Cancel event | Pending notice invalidated | Preserve original; review correction | Exact affected occurrence only |
| Change source | Replan from current source | Preserve attempted payload | No stale requirement resent |
| Decline/complete | Verify sender and owned assignment | Apply once | Genuine provider identity plus replay refusal |
| Spoofed reply | Reject display-name/body identity | No mutation | Unchanged assignment/consent |
| Ambiguous result | Record attempt first | Mark unknown and reconcile | No automatic resend |

Induce ambiguity only with a bounded adapter test seam after a real attempt, never
by blasting repeated email. Save operation IDs and provider lookup evidence; if
reconciliation is unsupported, preserve unknown and stop that notice. Capture
changed-source citations and exact affected recipients privately, publishing only
sanitized fictional outcomes. Do not mark the matrix passed without actual runs.
