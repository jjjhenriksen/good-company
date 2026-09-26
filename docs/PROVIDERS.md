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
