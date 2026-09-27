# Runtime upgrade acceptance (#57)

Passed on the local ARM64 deployment, upgrading the supported image built from
`c3d67b8` to the image built from `8aa3621` with existing nonempty state. See
[`completed-runtime-result.json`](../../eval/adoption/upgrade/completed-runtime-result.json).

All tables in the operating ledger, original live-test ledger, scheduled-test
ledger and provider journal retained identical row hashes across replacement.
The Index install identity and stored registration state were unchanged. The new
runtime's 28 Python modules, examples and four custom skills matched committed
source. All four custom skills and inherited browser, canvas, Google Workspace
and owner-Mac skills were eligible; the three obsolete custom skills were absent.

Exactly one Good Company operational job survived with its original ID, alongside
three inherited background jobs. It was rearmed for a single real scheduled tick
against the same test scope after the upgrade. The tick refreshed the connected
account and scoped calendar, planned the existing event/task work, and made zero
calls to the send method. The original two provider operations and receipts stayed
intact. A guard would have failed the test if any new send had been attempted; it
was never invoked. The test scope was paused, job disabled and original Gatekeeper
policy restored afterward.

This verifies replacement of supported application images and loaded skills on
the same pinned base. It does not claim an upstream OpenClaw version jump or a
public-image fresh install; those require their own validation when performed.
