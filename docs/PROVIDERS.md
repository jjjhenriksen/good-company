# Calendar and mail provider contract

`good_company.providers` is the domain/provider boundary. It currently has contract
fixtures; those are **not a live adapter or delivery proof**. Implementations must
use actually available authenticated tools. Never construct account permissions
from event text, an email display name, or a model's assertion.

An account exposes stable provider/account identity, verified sender, exact readable
calendar scopes and separate permissions for reads, unattended sends, native
idempotency and receipt reconciliation. Unavailable permissions fail before a claim.
Only genuine provider support may set `idempotent_send`; a local claim does not
create provider idempotency.

Calendar reads must expand recurring occurrences with stable IDs, enumerate every
page within the requested exact scope/window, and certify each page complete.
Only a fully exhausted read is imported. Partial reads, cursor loops, duplicate
occurrences, wrong scope and excessive pages/events are refused without replacing
the previous calendar. Adapters must enforce window/scoping at the provider query;
the domain engine also validates normalized event times.

Delivery claims the exact authorized payload once, then invokes the provider.
`accepted` requires a real stable provider receipt; it does not prove inbox delivery
or reading. `failed` requires a definite provider rejection. Timeouts or malformed
responses become `unknown`/uncertain, including exceptions after acceptance. No
automatic retry is permitted. Reconciliation looks up the same operation in the
same authenticated account; without that capability, leave an explicit exception.
Provider authentication errors must use safe codes, not secret-bearing response
bodies. Credentials and private messages stay outside source control and artifacts.

Run `python -m unittest discover -s tests -p test_providers.py -v` for fictional
contract checks. Live Google/Latch and a concrete second pilot provider remain
separate acceptance requirements in #30 and #31.

## Inbound identity boundary

`apply_verified_reply` fetches a `VerifiedReply` from the provider's authenticated
integration path. The same path handles genuine and spoofed contract fixtures.
There is deliberately no CLI accepting a caller's `authenticated: true` assertion.
A real adapter must prove sender identity independently of the From display name,
body text, and model assertions. If its tools cannot do so, the capability is
unavailable; do not process replies through this path.

A unique verified roster address may decline/complete only its own assignment,
stop its own communications, or set its own validated preferences. The identity
check, state change and replay receipt share one transaction. Only an opaque
provider evidence reference is retained, not the message body or credentials.
The trusted-operator CLI remains powerful; this does not create a public-user
sandbox. Live genuine/spoofed provider acceptance remains unverified (#29).

### Live connection recovery (2026-09-26)

The original HTTP 503 was specifically `Device is not connected`. Installed the
official signed Plow Latch app; the owner completed setup and connected Google.
The deployed agent now discovers 15 MCP tools. Its actual `plow-gog accounts`
call completed through Latch, followed by a calendar listing and a bounded timed
calendar read with an empty complete result and no next-page cursor. The account
owns its primary calendar. Private account/calendar identifiers remain outside
this repository.

The live Google Workspace skill describes a per-command approval boundary.
Observed behavior is more specific: the AI Gatekeeper reviewed and allowed three
owner-authorized fictional self-emails, but denied the fictional STOP reply as
outside its current family-errand scope. A human click is not necessarily required
for every send; an applicable Gatekeeper decision is. Existing policy does not
establish a standing Good Company unattended-send remit. Keep
`Account.unattended_send` false until that capability is genuinely established.
Do not bypass Latch, alter a denied request to evade review, or treat success on
one send as blanket authorization. The denied reply was not retried.

Actual self-test results: three Gmail acceptance IDs, received-message evidence,
one private transparent calendar fixture without guests, and refused second
claims for the core event and task notices. These are reviewed self-tests; they
do not prove scheduled unattended delivery or external-participant reply identity.

The probe now distinguishes the disconnected-device response without echoing
arbitrary provider error bodies. Tool discovery and successful reads are useful
progress, but this draft still does not implement or prove the full delivery and
verified-reply adapter required by #30.
