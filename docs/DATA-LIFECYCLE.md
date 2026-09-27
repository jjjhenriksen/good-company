# Owner-authorized data lifecycle

These are trusted-owner tools in the private single-organization runtime, not
participant-facing endpoints. Every operation requires an owner authority reference;
that audit string is not authentication. Keep the database and exports private.

- `export-summary`: reproducible aggregate table counts, without addresses, message
  text, credentials or skill assessments. This is not a full personal-data export.
- `delete-source`: withdraw a source first, then erase stored general text, dress
  rules and archived document versions. Retain the source tombstone and audit
  references so a stale source cannot silently re-enter use. External original
  files and existing private backups require their own authorized deletion.
- `retain-delivery-history`: remove content from finalized sent/failed messages
  before an explicit cutoff. Keep minimal recipient routing, receipt IDs, source
  revision/assignment IDs and attempt tombstones to prevent replay. Pending and
  ambiguous sends retain their evidence for reconciliation. Repeated runs are
  idempotent; delivery history itself is not purged.

This intentionally bounded scope does not claim full roster erasure or legal
retention compliance. Configure any broader deletion policy with the organization,
including suppression/deduplication requirements and backup retention, before
adding it. Never delete ledger rows merely to make the database smaller: that can
cause a previously accepted message to be sent again.
