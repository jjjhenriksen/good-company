# Arts nonprofit: rehearsal-change laboratory

Refs #59. Run `python scripts/adoption_lab.py --issue 59 --report /new/private/report.json`.
Uses the private loopback service documented in [the food bank lab](58-food-bank-lab.md).
It does not use real event sources, identities or mail delivery.

Two fictional programs have separate recipients: Alex receives arts notices, Sam
receives food-program notices. Event-linked setup tasks require each program's role.
The scenario first accepts both event notices and both task assignments locally.
A complete fictional calendar snapshot then removes the rehearsal while retaining
the food event. The arts task impact retains its attempted receipt; its queued
follow-up is cancelled, while the other program's task remains open.

Reviewed corrections for the rehearsal and its setup retain the original audience
and hidden-recipient rules. Two local correction receipts are saved. Repeated
correction creation resolves to the same ID, repeated sends fail, and the original
event receipts remain unchanged. A separate move case rejects a correction that
tries to substitute the food program's recipient for the arts audience.

Observed outcomes: six local notices accepted, including two corrections; zero
cross-team correction recipients; original receipts preserved; cancelled linked
follow-up cannot be sent; duplicate correction attempts refused.

The report contains counts and asserted outcomes, not raw messages or credentials.
Calendar data is explicitly fictional and imported as a complete supplied snapshot;
this does not prove native recurring-event completeness or live synchronization.
Issue #59 remains open for controlled real source changes, an authorized test mailbox
and genuine correction delivery evidence. The laboratory exercises the domain and
HTTP provider boundary without claiming that external acceptance has happened.
