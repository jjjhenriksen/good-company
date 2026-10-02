# Mutual aid: verified opt-out laboratory

Refs #60. Run `python scripts/adoption_lab.py --issue 60 --report /new/private/report.json`.
Uses the isolated HTTP mailbox described in [the food bank lab](58-food-bank-lab.md).

The scenario queues both a group event notice and separate helper task notices.
A Pat credential claiming Alex's address cannot apply STOP. Alex's own credential-bound
STOP invalidates the old event notice and cancels every pending task notice addressed
to Alex. Repeated processing is refused. A fresh event notice reaches only Sam,
and Sam's unaffected task assignment is also accepted locally.

Both sends consume the same two-message daily budget. An additional due assignment
is refused after reopening the coordination database, proving the budget and withdrawn
consent persist across process state. Accepted mailbox records contain only Sam as
a recipient: zero subsequent notices reach the stopped helper. A second case proves
that paused sending still permits verified STOP while preventing outbound work.

Observed outcomes: two local notices accepted; zero stopped-helper notices; shared
event/task budget used twice; a third notice refused; consent and budget survive
restart; spoofed and repeated STOP refused. Private reports contain these outcomes,
without message bodies, headers, participant credentials or raw authentication evidence.

The mailbox uses fictional identities and credential checks, not a real DKIM service.
Issue #60 remains open for an authorized genuine mailbox run through the independent
native identity bridge. No real recipients were contacted by these checks.
