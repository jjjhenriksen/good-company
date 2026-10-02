# Schema upgrades and recovery

Schema version 1 adopts the existing additive table layout. Opening an older
unversioned database first creates a private, integrity-checked SQLite snapshot
beside it, then applies all domain-table DDL and the version marker in one
transaction. Stored authority, consent, payloads, attempts and receipts are not
rewritten. A DDL failure rolls back and leaves the snapshot. Newer schema versions
are refused by older version-aware code. Future changes must advance this version
with an explicit tested migration; adding columns ad hoc is unsupported.

Before upgrading, stop the runtime and take the whole-state backup in BACKUP.md,
including both volumes. The per-database snapshot does not include Plow install
identity, credentials or scheduler state. Verify the candidate while delivery is
paused, then resume only after receipts and identity match.

Rollback is supported **only before new operational work or sends occur**: stop,
restore the complete pre-upgrade state into fresh volumes, and use its matching
image. Once any work has run, prefer a forward fix. Never restore a stale ledger
and restart sending: it can replay accepted messages. Reconcile all subsequent
provider receipts/unknown attempts before any exceptional recovery; do not erase
claims to make a retry possible. Pre-version releases do not have the newer-schema
guard and must never be pointed at an upgraded database.

Schema version 2 adds optional workflow policy, record and notice tables in the
same backed-up transaction. Existing v1 authority, receipts, replay tombstones
and optional tables from the initial module release are preserved. The version
advance prevents v1 code from opening a ledger whose optional notice attempts
must count toward the shared budget. All coordinator entrypoints migrate through
the same guard. New optional notices appear in aggregate readiness, health,
weekly delivery exceptions and export counts.
