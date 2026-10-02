# Apple PIM provider contract

`ApplePIMProvider` uses the existing domain provider protocol. Calendar aliases map
to exact native IDs supplied by the owner; account discovery and calendar inventory
must both prove access. The reader requests 10,001 events, one more than the domain
payload cap, and refuses a full prefix, mismatched counts, degraded or cross-calendar
records. A rejected refresh leaves the previous snapshot untouched. Complete empty
reads retire known missing events and their queued work through the existing engine.

Timed nonrecurring events use native IDs within the selected local store. Recurring
events require `seriesId` and `occurrenceOrigin`; identity uses the original occurrence,
never its current start. All-day events require `allDayStart`/`allDayEnd` floating
dates. The installed exporter omits these additional fields, so those cases are
refused until a native exporter supplies and validates them. A free/busy projection
preserves overlap checks and exposes only an existing-commitment label.

Mail reads reuse the verified-reply bridge from #29. Outbound delivery is unavailable:
Mail.app's success text does not carry an operation-bound acceptance receipt or
reconciliation result. The account advertises no unattended/idempotent/reconciled
sending, and its send/reconcile methods refuse without invoking the mail tool.

Contract regressions cover completeness, exact scope, stable moved-instance identity,
unsupported evidence, cancellation and title privacy. They use fictional native data.
Live acceptance still needs an authorized scoped calendar/mailbox, the native
occurrence/date/identity-binding extensions and a genuine receipt path. Issue #31
remains open for that full evidence; this PR delivers the bounded supported reader.
