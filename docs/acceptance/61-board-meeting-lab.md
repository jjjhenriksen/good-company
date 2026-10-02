# Board meeting: scoped reminder and private availability laboratory

Refs #61. Run `python scripts/adoption_lab.py --issue 61 --report /new/private/report.json`.
Uses the isolated service documented in [the food bank lab](58-food-bank-lab.md).

The fictional board has a scoped online-meeting event with an explicit
not-applicable dress setting and no dress-rule records. Its routine reminder receives
standing authorization, includes the meeting link and contains no invented attire.
The local HTTP mailbox accepts it once for the authorized board audience; replanning
creates no new notice and a repeated send is refused.

The HTTP laboratory also exposes one explicitly selected fictional personal calendar.
The actual NativeApplePIM client and ApplePIMProvider availability reader check an
overlapping commitment. The returned owner-facing message says there is an existing
commitment, with no private title or location. That privacy-safe message appears in
the report; the private event is never imported into the shared coordination database
or included in the group reminder. An unselected calendar is refused.

The second case shows that not-applicable dress never authorizes an out-of-scope
meeting. No local send is accepted for that case.

Observed outcomes: one local notice accepted, zero dress rules required, private
conflict communicated without its title, selected-calendar scope enforced, and repeat
send refused. All four adoption scenarios now run in CI on Python 3.11–3.13 and print
privacy-safe reports to the retained job log. Report files are private and refuse
overwrites. Neither local calendar reads nor loopback receipts establish actual
Apple calendar/mail acceptance. Issue #61 remains open for an authorized genuine
mailbox run with real delivery and deduplication evidence.
