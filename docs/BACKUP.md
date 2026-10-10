# Private backup and restore

These helpers operate on an **offline private state directory**, not a public
artifact. Stop the gateway and its operational scheduler first. Confirm no other
process writes the directory; the `offline=True` argument is an operator assertion,
not process detection. Preserve the entire state directory so the reporter's
install identity, operating remit and provider histories travel together.

From a trusted Python operator session:

```python
from good_company.state_backup import backup_state, restore_state, verify_backup
backup_state('/private/stopped-state', '/private/backups/snapshot-001', offline=True)
verify_backup('/private/backups/snapshot-001')
restore_state('/private/backups/snapshot-001', '/private/recovered-state', offline=True)
```

Check a retained snapshot without a restore destination:

```sh
python -m good_company.state_backup /private/backups/snapshot-001
```

Verification reads the manifest and its recorded files and directories, checking
the same paths, file modes and checksums as restore. It creates no directories,
opens no live database, and returns JSON containing only verification status,
format and counts. Format 1 snapshots have no explicit directory records, so
their directory count is zero. Invalid snapshots produce a nonzero exit status.
Keep the snapshot unchanged while verifying it. A checksum match verifies
consistency with the manifest; it does not authenticate who created the backup
or prove that the restored runtime and provider connections work.

Use actual private absolute paths outside Git repositories and public outputs.
The destination must not exist. Snapshots use SQLite's backup API and integrity
check, private file modes, and a checksum manifest. Restore validates all content
before atomically publishing the new directory. Existing state is never replaced.
Symlinks and special files are refused for explicit review; do not silently omit
linked identity data. Restore the verified directory as the stopped instance's
state volume, preserving its container uid/gid as required by deployment.

Before resuming, verify the install identity, standing remit and original provider
receipts, then enable exactly one scheduler. A restored accepted/uncertain claim
must never be replayed. Keep the prior directory until recovery is verified.
The fixture test proves ledger recovery; live base-image upgrade and scheduler
acceptance remain separate (#57). Backups may contain credentials and personal
data and must never enter Git, logs, PR attachments or public outputs.
