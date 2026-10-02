# Second provider decision (#31)

The owner selected Apple PIM for a local testing instance on October 1, 2026.
[PR #213](https://github.com/jjjhenriksen/good-company/pull/213) implements the
existing provider contract for explicitly selected Apple calendars without changing
domain coordination logic. It uses the read-only NativeApplePIM client and the
mailbox-bound identity policy introduced by [#212](https://github.com/jjjhenriksen/good-company/pull/212).

Supported scope: exact-account reads, explicit calendar IDs, bounded complete
non-recurring timed-event snapshots, sparse cancellations, and private overlap checks.
Recurring events require original occurrence identity; all-day events require floating
date evidence. The installed exporter lacks those fields, so the adapter refuses
such records. Installed auth results lack exact-message binding, so domain reply
changes remain unavailable through that legacy result. Native send and reconciliation
raise explicit unsupported errors; display text is not a provider receipt.

See the [adapter evidence and limitations](../acceptance/31-apple-pim-provider.md).
Local contract tests and the isolated HTTP adoption lab prove the code boundaries.
They do not establish native live sync, genuine incoming authentication or delivery.
Keep #31 open for missing native evidence and an authorized genuine mailbox run.
